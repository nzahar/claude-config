"""Does the grammar compiler accept D2's three split analysis contracts?

Sends one minimal grammar call per contract through the project's own Anthropic
boundary, so the request is built exactly as production builds it. Prints, per
contract, its size on the plan's basis and whether the compiler took it.

Read-only against the API in the sense that matters here: three small calls, each
asking for a handful of output tokens. Nothing is written anywhere.
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic

from commercial_proposals_helper.providers.boundary import (
    AnthropicStructuredProvider,
    ProviderError,
)
from commercial_proposals_helper.providers.schema import (
    anthropic_provider_schema,
    strict_provider_schema,
)

REPO = Path(os.environ.get("CPH_REPO", "/root/Projects/commercial_proposals_helper"))
if not (REPO / "pyproject.toml").exists():
    raise SystemExit(f"not a checkout: {REPO} (set CPH_REPO)")

SCHEMA = REPO / "schemas/v1/analysis-provider-output.schema.json"
WORKFLOW_CONFIG = REPO / "config/proposal-workflow/v1.json"

SPLITS: dict[str, list[str]] = {
    "brief+task_spec": ["lead_brief", "task_spec"],
    "units": ["work_units"],
    "roles+contradictions": ["speaker_roles", "policy_contradictions"],
    # The fallback §Goal names if brief+task_spec is refused.
    "lead_brief (fallback split)": ["lead_brief"],
    "task_spec (fallback split)": ["task_spec"],
}

# The positive control. Grounding review is the one contract measured as accepted in
# production, so if it is refused here the request shape is at fault and the run says
# nothing whatever about size.
CONTROL = REPO / "schemas/v1/grounding-review-provider-output.schema.json"


@dataclass(frozen=True, slots=True)
class ProbeAssets:
    model_id: str
    prompt: str
    prompt_version: str
    output_schema: dict[str, Any]
    reasoning_effort: str
    max_output_tokens: int
    output_mode: str


def subset(full: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    schema = {k: v for k, v in full.items() if k not in ("properties", "required")}
    schema["properties"] = {k: full["properties"][k] for k in keys}
    schema["required"] = keys
    return schema


def compiled_bytes(schema: dict[str, Any]) -> int:
    """The plan's basis: adapted, every `$ref` expanded, `$defs` retained."""
    adapted = anthropic_provider_schema(strict_provider_schema(schema))

    def expand(node: Any, root: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/"):
                target = root
                for part in ref[2:].split("/"):
                    target = target[part]
                return expand(target, root)
            return {k: expand(v, root) for k, v in node.items()}
        if isinstance(node, list):
            return [expand(v, root) for v in node]
        return node

    return len(json.dumps(expand(copy.deepcopy(adapted), adapted), ensure_ascii=False).encode())


async def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    full = json.loads(SCHEMA.read_text())
    pricing = json.loads(WORKFLOW_CONFIG.read_text())["pricing"]

    client = AsyncAnthropic(api_key=key, max_retries=0)
    provider = AnthropicStructuredProvider(
        client,
        pricing=pricing["models"],
        currency=pricing["currency"],
        pricing_version=pricing["version"],
    )

    cases = [("CONTROL grounding review", json.loads(CONTROL.read_text()))]
    authored = os.environ.get("CPH_CONTRACTS")
    if authored:
        # Step 2's exit condition: the files as authored, not the subsets §Goal measured.
        for slug in authored.split(","):
            path = REPO / f"schemas/v1/{slug}-provider-output.schema.json"
            cases.append((f"authored {slug}", json.loads(path.read_text())))
    else:
        cases += [(label, subset(full, keys)) for label, keys in SPLITS.items()]

    total = Decimal("0")
    refused: list[str] = []
    other: list[str] = []
    try:
        for label, schema in cases:
            size = compiled_bytes(schema)
            assets = ProbeAssets(
                model_id="claude-opus-5",
                prompt=(
                    "Return the smallest possible valid instance of the schema. "
                    "Invent nothing beyond what the schema demands."
                ),
                prompt_version="fit-probe",
                output_schema=schema,
                # "high" is what every stage config pins and what `assets.py:108`
                # asserts; sending anything else would make a 400 unattributable.
                reasoning_effort="high",
                max_output_tokens=2048,
                output_mode="grammar",
            )
            try:
                _document, usage = await provider.run(
                    "fit_probe", assets, {"note": "grammar fit probe, minimal instance"}
                )
            except ProviderError as error:
                billed = getattr(error, "usage", None)
                if billed is not None and billed.cost is not None:
                    total += billed.cost
                # Only a request-level rejection speaks to the compiler. The three
                # subclasses are model-side outcomes and say nothing about size.
                request_level = type(error) is ProviderError
                (refused if request_level else other).append(label)
                verdict = "REFUSED " if request_level else "model-side"
                print(
                    f"{label:30s} {size:6d} B  {verdict}  {type(error).__name__}"
                    f"  cause={error.__cause__!r}"
                )
                continue
            if usage.cost is not None:
                total += usage.cost
            print(f"{label:30s} {size:6d} B  accepted   ${usage.cost or 0:.4f}")
    finally:
        print(f"\ntotal spent: ${total:.4f}")

    print("refused by the compiler:", ", ".join(refused) if refused else "none")
    if other:
        print("model-side outcomes (not size evidence):", ", ".join(other))
    if any(label.startswith("CONTROL") for label in refused + other):
        print("\nCONTROL DID NOT PASS — this run says nothing about contract size.")
        return 2
    return 1 if refused else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
