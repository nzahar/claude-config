"""Run the split analysis stage for real, on the real 71-turn transcript.

Step 6 of `docs/plans/analysis-three-calls.md`. Everything below the provider is
the shipped code: the stage, its assets, the recorder, the artifact builder. Only
the surroundings are scaffolding — a throwaway SQLite file seeded with the
transcript pulled read-only from the test contour.

What it prints is what the plan gates on: the artifact's shape against today's,
and the per-call ledger with its cost.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO = Path(os.environ.get("CPH_REPO", "/root/Projects/commercial_proposals_helper"))
if not (REPO / "pyproject.toml").exists():
    raise SystemExit(f"not a checkout: {REPO} (set CPH_REPO)")

ARTIFACT = Path(__file__).with_name("real_artifact.json")
DB = Path(__file__).with_name("live_analysis.db")

from commercial_proposals_helper.analysis.assets import ANALYSIS_CALLS, AnalysisAssets  # noqa: E402
from commercial_proposals_helper.pipeline import analysis as stage  # noqa: E402
from commercial_proposals_helper.pipeline.deps import (  # noqa: E402
    PipelineDeps,
    StageContext,
    StageRecorder,
)
from commercial_proposals_helper.providers.boundary import (  # noqa: E402
    AnthropicStructuredProvider,
)
from commercial_proposals_helper.tables import (  # noqa: E402
    Base,
    Job,
    JobStatus,
    Project,
    StageRun,
    Transcript,
)


async def main() -> int:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2
    if DB.exists():
        DB.unlink()

    real = json.loads(ARTIFACT.read_text())
    turns = real["turns"]
    print(f"transcript: {len(turns)} turns")

    assets = AnalysisAssets.load(REPO / "config/analysis/v1.json")
    pricing = json.loads((REPO / "config/proposal-workflow/v1.json").read_text())["pricing"]
    provider = AnthropicStructuredProvider(
        AsyncAnthropic(api_key=key, max_retries=0),
        pricing=pricing["models"],
        currency=pricing["currency"],
        pricing_version=pricing["version"],
    )

    engine = create_async_engine(f"sqlite+aiosqlite:///{DB}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    project_id = uuid.uuid4()
    async with session_factory() as session:
        session.add(Project(id=project_id, name="live analysis split"))
        job = Job(project_id=project_id, kind="proposal", status=JobStatus.RUNNING, attempt=1)
        session.add(job)
        session.add(
            Transcript(
                project_id=project_id,
                raw_text="\n".join(f"{t['speaker_label']}: {t['text']}" for t in turns),
                turns=turns,
            )
        )
        await session.commit()
        job_id = job.id

    deps = PipelineDeps(
        settings=None,
        provider=provider,
        stage_assets=dict(assets.stages),
        analysis_assets=assets,
        proposal_assets=None,
        storage=None,
    )
    recorder = StageRecorder(session_factory, project_id, job_id)
    async with session_factory() as session:
        try:
            await stage.run(
                StageContext(
                    stage="analysis",
                    session=session,
                    project_id=project_id,
                    job_id=job_id,
                    deps=deps,
                    record=recorder.record,
                )
            )
            await session.commit()
        except Exception as error:
            print(f"\nSTAGE RAISED: {type(error).__name__}: {error}")
            await session.rollback()

    await report(session_factory, real)
    await engine.dispose()
    return 0


async def report(session_factory: Any, real: dict[str, Any]) -> None:
    import sqlalchemy as sa

    async with session_factory() as session:
        artifact = await session.scalar(sa.select(Transcript.analysis))
        runs = list((await session.execute(sa.select(StageRun))).scalars().all())

    print("\nLEDGER")
    total = Decimal("0")
    for run in sorted(runs, key=lambda r: r.created_at):
        cost = run.cost or Decimal("0")
        total += cost
        print(
            f"  {run.stage:16s} in {run.input_tokens or 0:6d}  out {run.output_tokens or 0:6d}"
            f"  ${cost:.4f}  raw_output={'yes' if run.raw_output else 'NO'}"
        )
    print(f"  {'total':16s} ${total:.4f}")

    if not isinstance(artifact, dict):
        print("\nNO ARTIFACT")
        return

    print("\nARTIFACT")
    print("  keys:", sorted(artifact))
    expected = {"provider", "model", "transcript", "lead_brief", "task_spec", "work_units"}
    print("  shape matches today's:", set(artifact) == expected, "" if set(artifact) == expected else sorted(set(artifact) ^ expected))
    spec = artifact.get("task_spec") or {}
    brief = artifact.get("lead_brief") or {}
    units = artifact.get("work_units") or []
    print("  task_spec id server-generated:", bool(spec.get("id")) and bool(spec.get("version_id")))
    print("  scope items:", len(spec.get("scope") or []), " assumptions:", len(spec.get("assumptions") or []))
    print("  policy_contradictions:", len(brief.get("policy_contradictions") or []))
    print("  work units:", len(units), [u.get("unit_id") for u in units])
    print("  hours:", [u.get("hours") for u in units])
    roles = {t.get("speaker_label"): t.get("speaker_role") for t in (artifact["transcript"]["turns"])}
    print("  speaker roles:", roles)
    print("  baseline for comparison: 20.5 h / 100,040 RUB over 5 units")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
