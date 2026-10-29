"""Opt-in live end-to-end smoke: DeepSeek -> Qloo -> deterministic rules.

Run only when explicitly requested (from ``backend``)::

    python -m scripts.plan_e2e_smoke --live

or set ``RUN_LIVE_SMOKE=1``. The script uses local environment/``backend/.env``
credentials, starts a signed game, advances the three NPC interactions with the
rules engine, and submits a free-text plan through the real HTTP route. DeepSeek
interprets the text, Qloo supplies real IDs, and Task 06 selects the score and
ending.

Output is deliberately limited to status and counts: no keys, entity IDs,
labels, model prose, request bodies, or raw provider responses.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.rules import record_npc_interaction  # noqa: E402
from app.core.state_security import sign_state  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.game import GameState, Plan  # noqa: E402
from app.services.plan_service import PlanService  # noqa: E402
from app.services.qloo_service import QlooConfigurationError  # noqa: E402

NPC_IDS = ("mara", "jun", "theo")
FREE_TEXT = "A town night with Inception, jazz records, and ramen."


def _opted_in(argv: list[str]) -> bool:
    if "--live" in argv:
        return True
    return os.getenv("RUN_LIVE_SMOKE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _safe_close(service: PlanService) -> None:
    asyncio.run(service.aclose())


def run_live() -> int:
    try:
        service = PlanService.from_env()
    except QlooConfigurationError:
        print("status=config_missing qloo=missing")
        return 2

    if service.deepseek is None:
        _safe_close(service)
        print("status=config_missing deepseek=missing")
        return 2

    try:
        app = create_app(plan_service_factory=lambda: service)
        with TestClient(app) as client:
            start = client.post(
                "/api/game/start",
                json={
                    "player_interests": {
                        "movies": ["Inception"],
                        "music": ["jazz"],
                        "food": ["ramen"],
                    }
                },
            )
            if start.status_code != 200:
                print(f"status=http_error phase=start http={start.status_code}")
                return 1

            start_body = start.json()
            state = GameState.model_validate(start_body["state"])
            for npc_id in NPC_IDS:
                state = record_npc_interaction(state, npc_id).state
            token = sign_state(state)

            response = client.post(
                "/api/plan/evaluate",
                json={
                    "state": state.model_dump(mode="json"),
                    "state_token": token,
                    "plan": Plan(free_text=FREE_TEXT).model_dump(),
                },
            )

        if response.status_code != 200:
            code = response.json().get("error", {}).get("code", "unknown")
            stats = service.last_stats
            print(
                "status=http_error phase=plan "
                f"http={response.status_code} code={code} "
                f"deepseek_attempted={stats.deepseek_attempted} "
                f"deepseek_ok={stats.deepseek_succeeded} "
                f"deepseek_errors="
                f"{','.join(stats.deepseek_error_codes) or 'none'} "
                f"qloo_calls={stats.qloo_calls}"
            )
            return 1

        body = response.json()
        stats = service.last_stats
        evidence_count = len(body.get("evidence", []))
        print(
            "status=ok "
            f"deepseek_attempted={stats.deepseek_attempted} "
            f"deepseek_ok={stats.deepseek_succeeded} "
            f"deepseek_errors={','.join(stats.deepseek_error_codes) or 'none'} "
            f"qloo_calls={stats.qloo_calls} "
            f"qloo_errors={stats.qloo_errors} "
            f"evidence={evidence_count} "
            f"evidence_status={body.get('evidence_status')} "
            f"interpretation={body.get('interpretation_status')} "
            f"score={body.get('score')} "
            f"ending={body.get('ending')} "
            f"stage={body.get('state', {}).get('stage')}"
        )

        if stats.deepseek_attempted < 1 or stats.deepseek_succeeded < 1:
            print("status=fail deepseek=not_executed")
            return 1
        if stats.qloo_calls < 1:
            print("status=fail qloo=not_executed")
            return 1
        if stats.qloo_errors:
            print("status=fail qloo=errors_present")
            return 1
        if evidence_count < 1:
            print("status=fail qloo=no_evidence")
            return 1
        if body.get("state", {}).get("stage") != "complete":
            print("status=fail rules=not_applied")
            return 1

        print("result=PASS")
        return 0
    finally:
        _safe_close(service)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not _opted_in(arguments):
        print("status=skipped pass=--live")
        return 0
    try:
        return run_live()
    except KeyboardInterrupt:
        print("status=interrupted")
        return 130
    except Exception as exc:  # Never print provider messages or payloads.
        print(f"status=error error_type={type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
