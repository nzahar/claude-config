"""Pre-flight for the prose branch: one paid composition call, then the real layer.

The difference from `prose_probe.py`, which this supersedes: the prompt, the
payload and every check are the ones the branch actually ships. The probe
measured whether prose was viable at all; this measures whether the code that
was written on the back of that answer holds on real material, before a full
contour run is bought.

Reports, in order:

  findings   -> `proposal.markdown.review` over the answer, with the real islands
  headings   -> the profile's sections, presence and order
  islands    -> the five placeholders, each exactly once, each in its section
  numerals   -> the D9 scan split into marker-carrying (raises) and bare (does not)
  anchors    -> resolved, and the two failure kinds kept apart
  leakage    -> the pinned term sets over the assembled document

Streams and sets `max_retries=0`, matching the boundary: a timeout here is
terminal by design, because it says nothing about whether the model finished.
Writes the raw answer next to this script so a second reading costs nothing.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from anthropic import AsyncAnthropic

REPO = Path(os.environ.get("CPH_REPO", "/root/Projects/commercial_proposals_helper"))
if not (REPO / "pyproject.toml").exists():
    raise SystemExit(f"not a checkout: {REPO} (set CPH_REPO)")
# Ahead of the editable install: pairing one branch's code with another branch's
# pinned prompt and hashes is exactly what the guard above reads as validated.
sys.path.insert(0, str(REPO / "src"))

from commercial_proposals_helper.pipeline.composition import (  # noqa: E402
    composition_payload,
    project_estimate,
    render_islands,
)
from commercial_proposals_helper.proposal.assets import ProposalAssets  # noqa: E402
from commercial_proposals_helper.proposal.markdown import (  # noqa: E402
    _ANCHOR,
    _BARE_RUN,
    _NUMERAL,
    _masked,
    ISLAND_SECTIONS,
    _LEAKAGE_CODES,
    review,
    sections,
    turn_texts,
)
from commercial_proposals_helper.proposal.provider_assets import (  # noqa: E402
    ProposalProviderAssets,
)
from commercial_proposals_helper.providers.boundary import _anthropic_contract  # noqa: E402
from commercial_proposals_helper.providers.usage_pricing import (  # noqa: E402
    priced_usage,
    read_anthropic_usage,
)

OUT = Path(__file__).with_name("prose_preflight_output.md")
ARTIFACT = Path(
    os.environ.get("CPH_ARTIFACT", Path(__file__).with_name("real_artifact.json"))
)


def _rows(artifact: dict[str, Any]) -> list[Any]:
    return [
        SimpleNamespace(
            unit_type=str(row["unit_type"]),
            title=str(row["title"]),
            hours=Decimal(str(row["hours"])),
            price=Decimal(str(row["price"])),
        )
        for row in artifact["estimates"]
    ]


async def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    real = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    if not real.get("turns"):
        raise SystemExit(f"{ARTIFACT} has no turns; anchors would measure nothing")

    assets = ProposalAssets.load(REPO / "config/proposals/v1.json")
    workflow = ProposalProviderAssets.load(REPO / "config/proposal-workflow/v1.json")
    stage = workflow.stages["composition"]
    artifact = {
        "lead_brief": real["lead_brief"],
        "task_spec": real["task_spec"],
        "work_units": real["work_units"],
        "transcript": {"turns": real["turns"]},
    }
    rows = _rows(real)
    projection = project_estimate(rows, assets.policy)
    payload = composition_payload(artifact, rows, projection, assets)

    client = AsyncAnthropic(api_key=key, max_retries=0)
    message = None
    try:
        # The request kwargs come from the boundary rather than being retyped:
        # the pinned `reasoning_effort` rides in `output_config`, and an answer
        # bought at the API default would describe a configuration that does not
        # ship. Serialisation and the cached system block are mirrored for the
        # same reason — they change the bytes the model sees and the bill.
        async with client.messages.stream(
            model=stage.model_id,
            max_tokens=stage.max_output_tokens,
            system=[
                {
                    "type": "text",
                    "text": stage.prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(
                        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
                    ),
                }
            ],
            **_anthropic_contract("composition", stage),
        ) as stream:
            try:
                message = await stream.get_final_message()
            except BaseException:
                # `BaseException`, not `Exception`: a 32k generation runs for
                # minutes and Ctrl-C is the likeliest interruption, so catching
                # only `Exception` would lose the partial answer and the counters
                # on a call that was billed anyway.
                try:
                    message = stream.current_message_snapshot
                except Exception:
                    message = None
                if message is not None:
                    partial = "".join(
                        block.text
                        for block in message.content
                        if getattr(block, "type", None) == "text"
                    )
                    if partial:
                        OUT.write_text(partial, encoding="utf-8")
                        print(f"partial answer saved: {OUT}")
                raise
    finally:
        if message is not None:
            # Priced from the registry the loader already parsed: a second read
            # of the config here could raise between the answer arriving and it
            # being written to disk.
            _, cost = priced_usage(
                workflow.model_pricing[stage.model_id],
                message.usage,
                reader=read_anthropic_usage,
            )
            print(f"cost: ${cost or 0:.4f}   stop_reason: {message.stop_reason}")

    markdown = "".join(
        block.text for block in message.content if block.type == "text"
    )
    try:
        OUT.write_text(markdown, encoding="utf-8")
    except OSError as error:  # never let a failed write destroy a paid answer
        print(f"could not save the answer ({error}); it follows in full:\n{markdown}")

    if message.stop_reason != "end_turn":
        print(
            f"\nstop_reason is {message.stop_reason}, not end_turn — the answer is "
            "incomplete and measuring it would blame the model for truncation."
        )
        return 1

    findings = report(markdown, assets, artifact, rows, projection)
    print(f"\nraw answer: {OUT}")
    return 1 if findings else 0


def report(
    markdown: str,
    assets: ProposalAssets,
    artifact: dict[str, Any],
    rows: list[Any],
    projection: Any,
) -> int:
    islands = render_islands(rows, projection, assets.policy)
    document, findings = review(
        markdown,
        profile=assets.profile,
        turns=turn_texts(artifact["transcript"]),
        leakage_terms=assets.leakage_terms,
        islands=islands,
        proposal_date=date.today(),
        maximum_age_days=assets.maximum_proposal_age_days,
    )

    print("\nFINDINGS   ", len(findings) or "none")
    for finding in findings:
        print(f"             {finding.code:24s} {finding.path:36s} {finding.message[:60]}")

    found = sections(markdown)
    offered = [kind.value for kind in assets.profile.block_order if kind.value != "cover"]
    required = [kind.value for kind in assets.profile.required_blocks if kind.value != "cover"]
    actual = [section.block_id for section in found]
    print("HEADINGS   ", f"{len(actual)} written, {len(offered)} offered")
    print("             outside the profile:", [n for n in actual if n not in offered] or "none")
    print("             missing required:", [n for n in required if n not in actual] or "none")
    print("             optional omitted:", [n for n in offered if n not in required and n not in actual] or "none")

    print("ISLANDS")
    for name in ISLAND_SECTIONS:
        token = "{{" + name + "}}"
        print(f"             {token:24s} {markdown.count(token)}")

    masked = _masked(markdown)
    hits = [m.group(0).strip() for m in _NUMERAL.finditer(masked) if m.group(0).strip()]
    carrying = [hit for hit in hits if not _BARE_RUN.match(hit)]
    bare = [hit for hit in hits if _BARE_RUN.match(hit)]
    print("NUMERALS   ", f"{len(carrying)} with a unit marker (raise), {len(bare)} bare (do not)")
    for sample in carrying[:12]:
        print("             unit ", repr(sample))
    for sample in bare[:8]:
        print("             bare ", repr(sample))

    turns = turn_texts(artifact["transcript"])
    anchors = [
        (match.group(1).strip(), match.group(2).strip())
        for match in _ANCHOR.finditer(markdown)
    ]
    unknown_turn = [pair for pair in anchors if pair[0] not in turns]
    unresolved = [item for item in findings if item.code == "unresolved_anchor"]
    lengths = sorted(len(quote) for _, quote in anchors)
    print("ANCHORS    ", f"{len(anchors)} written, {len(anchors) - len(unresolved)} resolved")
    print("             openings the regex could not read:", markdown.count("[[q:") - len(anchors))
    print("             cited a turn that does not exist:", len(unknown_turn))
    print("             right turn, quote not found:", len(unresolved) - len(unknown_turn))
    if lengths:
        print(
            f"             quote length: min {lengths[0]}, median "
            f"{lengths[len(lengths) // 2]}, max {lengths[-1]}"
            f"   (<=15 chars: {sum(1 for n in lengths if n <= 15)} — resolvable by luck)"
        )

    terms = sum(len(assets.leakage_terms.get(key, ())) for key in _LEAKAGE_CODES)
    leaked = [item.code for item in findings if item.code.endswith(("_leakage", "_term"))]
    print("LEAKAGE    ", f"{terms} terms checked ->", leaked or "none")
    print("DOCUMENT   ", f"{len(document)} chars assembled, {len(markdown)} written")
    return len(findings)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
