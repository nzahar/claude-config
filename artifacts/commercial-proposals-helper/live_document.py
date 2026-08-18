"""The prose document, bought for real, inside the deployed image.

Step 11 of `docs/plans/prose-document.md`. Everything below the provider is the
shipped code: the three stages, their pinned assets, the recorder, the
deterministic layer. Only the surroundings are scaffolding — a throwaway SQLite
seeded from the contour's own already-paid analysis artifact, read-only.

Seeding from that artifact rather than re-transcribing is what makes the
comparison mean something: the baseline of 63 findings was produced from this
exact `lead_brief`, `task_spec` and estimate, so any difference in the codes is
the document contract changing and not a different transcript.
"""

from __future__ import annotations

import asyncio
import collections
import json
import os
import sqlite3
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import sqlalchemy as sa

from commercial_proposals_helper.analysis.assets import AnalysisAssets
from commercial_proposals_helper.pipeline import composition, repair, review
from commercial_proposals_helper.pipeline.deps import (
    PipelineDeps,
    StageContext,
    StageRecorder,
)
from commercial_proposals_helper.providers.boundary import AnthropicStructuredProvider
from commercial_proposals_helper.proposal.assets import ProposalAssets
from commercial_proposals_helper.proposal.provider_assets import ProposalProviderAssets
from commercial_proposals_helper.rendering.html import HtmlRenderer
from commercial_proposals_helper.tables import (
    Base,
    Estimate,
    Job,
    JobStatus,
    Project,
    ProposalVersion,
    StageRun,
    Transcript,
)


ROOT = Path("/app")
SOURCE_DB = Path("/app/.data/app.db")
BASELINE_PROJECT = "d7c7c0ea00f8455eae1cfb7cb6794af8"
OUT = Path("/tmp/live_document")

# The first full contour run, read from this same database.
BASELINE = {
    "total": 63,
    "policy_provenance_mismatch": 31,
    "estimate_provenance_mismatch": 24,
}

STAGES = (
    ("composition", composition.run),
    ("grounding_review", review.run),
    ("repair", repair.run),
)


def _pull() -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """The paid artifact, the estimate rows and the project's name. Read-only."""
    db = sqlite3.connect(f"file:{SOURCE_DB}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    artifact = db.execute(
        "SELECT analysis FROM transcripts WHERE project_id = ?", (BASELINE_PROJECT,)
    ).fetchone()
    if artifact is None or not artifact["analysis"]:
        raise SystemExit("the baseline project has no analysis artifact")
    rows = db.execute(
        "SELECT * FROM estimates WHERE project_id = ? ORDER BY position", (BASELINE_PROJECT,)
    ).fetchall()
    name = db.execute(
        "SELECT name FROM projects WHERE id = ?", (BASELINE_PROJECT,)
    ).fetchone()
    db.close()
    analysis = artifact["analysis"]
    return (
        json.loads(analysis) if isinstance(analysis, str) else analysis,
        [dict(row) for row in rows],
        str(name["name"]) if name else "Клиент",
    )


async def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)

    artifact, rows, name = _pull()
    turns = (artifact.get("transcript") or {}).get("turns") or []
    print(f"seeded from the paid artifact: {len(turns)} turns, {len(rows)} estimate rows")
    print(f"client: {name}")

    proposal_assets = ProposalAssets.load(ROOT / "config/proposals/v1.json")
    workflow = ProposalProviderAssets.load(ROOT / "config/proposal-workflow/v1.json")
    analysis_assets = AnalysisAssets.load(ROOT / "config/analysis/v1.json")
    provider = AnthropicStructuredProvider(
        AsyncAnthropic(api_key=key, max_retries=0),
        pricing=workflow.model_pricing,
        currency=workflow.currency,
        pricing_version=workflow.pricing_version,
    )

    database = OUT / "live_document.db"
    if database.exists():
        database.unlink()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(Project(id=project_id, name=name))
        job = Job(project_id=project_id, kind="proposal", status=JobStatus.RUNNING, attempt=1)
        session.add(job)
        session.add(
            Transcript(
                project_id=project_id,
                raw_text="\n".join(str(turn.get("text", "")) for turn in turns),
                turns=turns,
                analysis=artifact,
            )
        )
        for row in rows:
            session.add(
                Estimate(
                    project_id=project_id,
                    position=row["position"],
                    unit_id=row.get("unit_id"),
                    unit_type=row["unit_type"],
                    title=row["title"],
                    hours=Decimal(str(row["hours"])),
                    price=Decimal(str(row["price"])),
                    precedents=(
                        json.loads(row["precedents"])
                        if isinstance(row["precedents"], str)
                        else row["precedents"]
                    ),
                    confidence=row["confidence"],
                    provenance=row["provenance"],
                )
            )
        await session.commit()
        job_id = job.id

    deps = PipelineDeps(
        settings=None,
        provider=provider,
        stage_assets=dict(workflow.stages),
        analysis_assets=analysis_assets,
        proposal_assets=proposal_assets,
        storage=None,
    )
    recorder = StageRecorder(session_factory, project_id, job_id)
    for stage_name, run in STAGES:
        print(f"\n── {stage_name} ──")
        async with session_factory() as session:
            try:
                await run(
                    StageContext(
                        stage=stage_name,
                        session=session,
                        project_id=project_id,
                        job_id=job_id,
                        deps=deps,
                        record=recorder.record,
                    )
                )
                await session.commit()
            except Exception as error:
                print(f"  STAGE RAISED: {type(error).__name__}: {error}")
                await session.rollback()
                break

    await report(session_factory, proposal_assets)
    await engine.dispose()
    return 0


async def report(session_factory: Any, assets: ProposalAssets) -> None:
    async with session_factory() as session:
        runs = list((await session.execute(sa.select(StageRun))).scalars().all())
        versions = list(
            (
                await session.execute(
                    sa.select(ProposalVersion).order_by(ProposalVersion.version_number)
                )
            )
            .scalars()
            .all()
        )

    print("\nLEDGER")
    total = Decimal("0")
    for run in sorted(runs, key=lambda item: item.created_at):
        cost = run.cost or Decimal("0")
        total += cost
        print(
            f"  {run.stage:18s} in {run.input_tokens or 0:6d}  out {run.output_tokens or 0:6d}"
            f"  ${cost:.4f}"
        )
    print(f"  {'total':18s} ${total:.4f}   (analysis and transcription already paid)")

    if not versions:
        print("\nNO VERSION")
        return

    for version in versions:
        codes = collections.Counter(item["code"] for item in (version.findings or []))
        sources = collections.Counter(item["source"] for item in (version.findings or []))
        print(f"\nVERSION {version.version_number}  ({version.status})")
        print(f"  findings: {sum(codes.values())}")
        for code, count in codes.most_common():
            print(f"    {code:34s} {count}")
        print(f"  by source: {dict(sources)}")

    final = versions[-1]
    codes = collections.Counter(item["code"] for item in (final.findings or []))
    print("\nAGAINST THE BASELINE")
    print(f"  baseline total: {BASELINE['total']}   now: {sum(codes.values())}")
    for code, count in BASELINE.items():
        if code == "total":
            continue
        print(f"  {code:34s} {count} -> {codes.get(code, 0)}")

    content = final.content
    document = content.get("document", "")
    markdown = content.get("markdown", "")
    print("\nDOCUMENT")
    print(f"  schema_version: {content.get('schema_version')}")
    print(f"  client_name:    {content.get('client_name')}")
    print(f"  proposal_date:  {content.get('proposal_date')}")
    print(f"  markdown {len(markdown)} chars -> document {len(document)} chars")
    print(f"  placeholders left in the document: {document.count('{{')}")
    print(f"  anchors: {markdown.count('[[q:')}")

    (OUT / "document.md").write_text(document, encoding="utf-8")
    (OUT / "source.md").write_text(markdown, encoding="utf-8")
    try:
        from commercial_proposals_helper.proposal.models import ProposalDocument

        html = HtmlRenderer(assets).render_html(ProposalDocument.model_validate(content))
        (OUT / "document.html").write_bytes(html)
        print(f"  rendered html: {len(html)} bytes")
    except Exception as error:  # noqa: BLE001 - the run's value is the findings
        print(f"  RENDER FAILED: {type(error).__name__}: {error}")
    print(f"\n  saved under {OUT}")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
