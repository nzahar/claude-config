"""What does the model actually do when asked for the proposal as prose?

One composition call, then five measurements against the raw markdown. Each
measurement corresponds to a guard the plan currently writes blind:

  headings   -> D5's closed-list heading check and `forbidden_block`
  placeholders -> D4's five islands surviving generation
  numerals   -> D14's `prose_numeric_literal` scan and §Numbers in prose
  anchors    -> D6's `[[q:turn-N|quote]]` and their resolvability
  leakage    -> `_check_static_text` re-pointed at markdown

The call streams and sets `max_retries=0`, matching the boundary's rules: a
timeout here is terminal by design, because it says nothing about whether the
model finished, and nothing may be re-bought silently.

Writes the raw answer next to this script so a second reading costs nothing.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic

from commercial_proposals_helper.providers.usage_pricing import (
    priced_usage,
    read_anthropic_usage,
)

REPO = Path(os.environ.get("CPH_REPO", "/root/Projects/commercial_proposals_helper"))
if not (REPO / "pyproject.toml").exists():
    raise SystemExit(f"not a checkout: {REPO} (set CPH_REPO)")
sys.path.insert(0, str(REPO / "tests"))

OUT = Path(__file__).with_name("prose_probe_output.md")
MODEL = "claude-opus-5"
PLACEHOLDERS = (
    "{{estimate_table}}",
    "{{subscription_plans}}",
    "{{comparison_table}}",
    "{{delivery_window}}",
    "{{disclaimers}}",
)
ANCHOR = re.compile(r"\[\[q:([^|\]]+)\|([^\]]+)\]\]")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
# Deliberately blunt, exactly as D14 describes it: digit runs, with or without a
# unit marker. Anchors are stripped before the scan — `turn-3` is not a claim about
# money — and a run glued to letters ("Битрикс24") is a name, not a figure.
NUMERAL = re.compile(
    r"(?<![\w-])\d[\d\s  .,]*(?![\w])\s*(?:%|₽|руб\w*|USD|\$|час\w*|дн\w*|недел\w*|месяц\w*)?"
)


def payload() -> dict[str, Any]:
    """The canned fixture by default; the real run's artifact when CPH_ARTIFACT points at one.

    The real file is what `transcripts.analysis` and `estimates` hold for the baseline
    project, pulled read-only from the test contour. Anchors resolve against its own
    `turns`, not against the evidence quotes — on real material the model may anchor to
    anything that was said, which is the whole point of asking.
    """
    profile = json.loads((REPO / "data/proposals/profile.v1.json").read_text())
    sections = [b for b in profile["block_order"] if b != "cover"]

    source = os.environ.get("CPH_ARTIFACT")
    if source:
        real = json.loads(Path(source).read_text())
        if not real.get("turns"):
            raise SystemExit(f"{source} has no turns; anchors would measure nothing")
        rows = real["estimates"]
        hours = sum(Decimal(str(row["hours"])) for row in rows)
        price = sum(Decimal(str(row["price"])) for row in rows)
        return {
            "lead_brief": real["lead_brief"],
            "task_spec": real["task_spec"],
            "work_units": real["work_units"],
            "estimate": {
                "currency": "RUB",
                "total_hours": str(hours),
                "total_price": str(price),
                "units": [
                    {k: str(row[k]) for k in ("unit_type", "title", "hours", "price")}
                    for row in rows
                ],
            },
            "turns": real["turns"],
            "sections": sections,
        }

    from fixtures.pipeline_outputs import analysis_output

    analysis = analysis_output()
    return {
        "lead_brief": analysis["lead_brief"],
        "task_spec": analysis["task_spec"],
        "work_units": analysis["work_units"],
        "estimate": {
            "currency": "RUB",
            "total_hours": "20.5",
            "net_price": "100040",
            "total_price": "100040",
            "delivery_days": 12,
        },
        "sections": sections,
    }


def prompt(sections: list[str]) -> str:
    listed = "\n".join(f"- {name}" for name in sections)
    return (
        "Ты пишешь коммерческое предложение на русском языке в формате Markdown.\n\n"
        "Разделы, ровно в этом порядке, по одному заголовку второго уровня на каждый; "
        "в заголовке — только идентификатор раздела из списка:\n"
        f"{listed}\n\n"
        "Сервер сам подставит все точные значения на место плейсхолдеров. Вставь их "
        "дословно, каждый на отдельной строке, и не пиши рядом ни одной цифры:\n"
        "- {{estimate_table}} — смета и стоимость, в разделе project_commercials\n"
        "- {{subscription_plans}} — тарифы подписки, в разделе subscription_alternative\n"
        "- {{comparison_table}} — сравнение, в разделе comparison\n"
        "- {{delivery_window}} — сроки, в разделе implementation_plan\n"
        "- {{disclaimers}} — обязательные оговорки, в разделе responsibilities_and_limits\n\n"
        "Любое утверждение о клиенте подкрепляй якорем вида [[q:turn-N|дословная цитата]], "
        "где turn-N и цитата взяты из входных данных без изменений.\n\n"
        "Никаких сумм, процентов, часов и сроков в тексте: их печатает сервер."
    )


async def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2

    data = payload()
    pricing = json.loads((REPO / "config/proposal-workflow/v1.json").read_text())["pricing"]
    client = AsyncAnthropic(api_key=key, max_retries=0)

    message = None
    try:
        async with client.messages.stream(
            model=MODEL,
            max_tokens=16000,
            system=prompt(data.pop("sections")),
            messages=[{"role": "user", "content": json.dumps(data, ensure_ascii=False)}],
        ) as stream:
            try:
                message = await stream.get_final_message()
            except Exception:
                # The call is billed whether or not it completed; losing the counters
                # is how a paid call reads as free (boundary.py:249-256). The snapshot
                # is a property that asserts, so getattr alone would not catch it.
                try:
                    message = stream.current_message_snapshot
                except Exception:
                    message = None
                if message is not None:
                    partial = "".join(
                        b.text for b in message.content if getattr(b, "type", None) == "text"
                    )
                    if partial:
                        OUT.write_text(partial, encoding="utf-8")
                        print(f"partial answer saved: {OUT}")
                raise
    finally:
        if message is not None:
            _, cost = priced_usage(
                pricing["models"], message.usage, reader=read_anthropic_usage
            )
            print(f"cost: ${cost or 0:.4f}   stop_reason: {message.stop_reason}")

    text = "".join(block.text for block in message.content if block.type == "text")
    try:
        OUT.write_text(text, encoding="utf-8")
    except OSError as error:  # never let a failed write destroy a paid answer
        print(f"could not save the answer ({error}); it follows in full:\n{text}")

    if message.stop_reason != "end_turn":
        print(
            f"\nstop_reason is {message.stop_reason}, not end_turn — the answer is "
            "incomplete and measuring it would blame the model for truncation."
        )
        return 1

    report(text, data)
    print(f"\nraw answer: {OUT}")
    return 0


def report(text: str, data: dict[str, Any]) -> None:
    profile = json.loads((REPO / "data/proposals/profile.v1.json").read_text())
    expected = [b for b in profile["block_order"] if b != "cover"]
    leakage = json.loads((REPO / "data/proposals/leakage-terms.v1.json").read_text())

    headings = [h.strip() for h in HEADING.findall(text)]
    unknown = [h for h in headings if h not in expected]
    print("HEADINGS   ", f"{len(headings)} found, {len(expected)} offered")
    print("            outside the profile:", unknown or "none")
    # D5's rule, not list equality: presence is owed only for required blocks, and
    # order is compared over what is actually present.
    required = [b for b in profile["required_blocks"] if b != "cover"]
    print("            missing required:", [b for b in required if b not in headings] or "none")
    present = [h for h in headings if h in expected]
    print("            order over the intersection:",
          "ok" if present == [b for b in expected if b in headings] else "WRONG")
    optional_omitted = [b for b in profile["optional_blocks"] if b not in headings]
    print("            optional omitted (legitimate):", optional_omitted or "none")

    print("PLACEHOLDERS")
    for token in PLACEHOLDERS:
        print(f"            {token:24s} {text.count(token)}")

    body = ANCHOR.sub(" ", text)
    body = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    body = re.sub(r"^\s*\d+[.)]\s", " ", body, flags=re.MULTILINE)  # ordered-list markers
    for token in PLACEHOLDERS:
        body = body.replace(token, "")
    hits = [m.group(0).strip() for m in NUMERAL.finditer(body) if m.group(0).strip()]
    carrying = [h for h in hits if re.search(r"[^\d\s  .,]", h)]
    bare = [h for h in hits if h not in carrying]
    print("NUMERALS   ", f"{len(carrying)} with a unit (money/percent/hours/days), {len(bare)} bare")
    for sample in carrying[:12]:
        print("             unit ", repr(sample))
    for sample in bare[:8]:
        print("             bare ", repr(sample))

    anchors = ANCHOR.findall(text)
    print("ANCHORS    ", f"{len(anchors)} written")
    resolved, failed = 0, []
    turns: dict[str, list[str]] = {}
    if data.get("turns"):
        # Real material: an anchor may quote anything that was actually said.
        for turn in data["turns"]:
            turns.setdefault(turn["turn_id"], []).append(turn["text"])
    else:
        for claims in _claims(data):
            for q in claims:
                turns.setdefault(q["turn_id"], []).append(q["quote"])
    # Two failures, deliberately not merged. On the canned fixture the payload hands
    # the model ready turn_id/quote pairs; on real material it hands none — provenance
    # there is opaque span ids — so the model must find the turn among 71 itself.
    # Merged, a retrieval miss and a sloppy copy are one number and the drop reads as
    # the wrong thing.
    unknown_turn, bad_quote = [], []
    lengths = []
    for turn_id, quote in anchors:
        turn_id, quote = turn_id.strip(), quote.strip()
        lengths.append(len(quote))
        sources = turns.get(turn_id, [])
        if not sources:
            unknown_turn.append((turn_id, quote[:40]))
        elif any(quote in source for source in sources):
            resolved += 1
        else:
            bad_quote.append((turn_id, quote[:40]))
    print("            resolved:", resolved)
    print("            cited a turn that does not exist:", len(unknown_turn))
    print("            right turn, quote not found in it:", len(bad_quote))
    if lengths:
        lengths.sort()
        print(
            f"            quote length: min {lengths[0]}, median "
            f"{lengths[len(lengths) // 2]}, max {lengths[-1]}"
            f"   (<=15 chars: {sum(1 for n in lengths if n <= 15)} — resolvable by luck)"
        )
    for item in (unknown_turn + bad_quote)[:8]:
        print("            unresolved:", item)

    all_terms = _terms(leakage)
    terms = [t for t in all_terms if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", text, re.I)]
    print("LEAKAGE    ", f"{len(all_terms)} terms checked ->", terms or "none")


def _claims(data: dict[str, Any]) -> Any:
    for section in ("lead_brief", "task_spec"):
        block = data.get(section) or {}
        for value in block.values():
            items = value if isinstance(value, list) else [value]
            for item in items:
                if isinstance(item, dict) and "evidence" in item:
                    yield item["evidence"]


def _terms(leakage: Any) -> list[str]:
    """Every term set, not the first one — the file holds three lists, 17 terms."""
    terms: list[str] = []
    if isinstance(leakage, dict):
        for value in leakage.values():
            if isinstance(value, list) and value and isinstance(value[0], str):
                terms.extend(value)
    return terms


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
