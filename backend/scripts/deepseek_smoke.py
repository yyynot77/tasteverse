"""Opt-in live DeepSeek -> Qloo tool-call smoke test.

This script intentionally contacts the real DeepSeek chat-completions endpoint
and the real Qloo API using local configuration (``backend/.env`` or process
environment). It prints only safe status/count information: no API keys,
entity IDs, labels, raw provider bodies, or model prose.

It is not part of the normal test suite. Run from ``backend``:

    python -m scripts.deepseek_smoke

The run passes only if DeepSeek actually requests ``search_cultural_entity``
and the existing Qloo client returns at least one real entity. A plain-text
answer with no tool call is a failure.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.orchestrator import AgentError  # noqa: E402
from app.agents.service import DialogueService  # noqa: E402
from app.core.config import DeepSeekConfigurationError  # noqa: E402
from app.models.game import GameState, PlayerInterests  # noqa: E402
from app.services.qloo_service import QlooConfigurationError  # noqa: E402

SMOKE_MESSAGE = (
    "Live integration check. Call search_cultural_entity with query "
    "'Inception' and entity_type 'urn:entity:movie' (take 2) before answering. "
    "Then name one returned title in one short sentence. Do not answer without "
    "making that tool call."
)
SEARCH_TOOL = "search_cultural_entity"


def _state() -> GameState:
    return GameState(
        player_interests=PlayerInterests(
            movies=["Inception"], music=["jazz"], food=["ramen"]
        )
    )


def _print_trace(service: DialogueService) -> None:
    traces = service.agent.last_tool_trace
    print(f"- tool_calls_executed: {service.agent.last_tool_calls_executed}")
    print(f"- tool_trace_entries: {len(traces)}")
    for entry in traces:
        print(
            f"  - {entry.tool}: status={entry.status} "
            f"result_count={entry.result_count} "
            f"error_code={entry.error_code or 'none'}"
        )


async def _run() -> int:
    try:
        service = DialogueService.from_env()
    except (DeepSeekConfigurationError, QlooConfigurationError) as exc:
        print(f"FAIL: configuration: {exc}")
        return 1

    try:
        async with service.deepseek, service.qloo:
            print("DeepSeek -> Qloo live smoke")
            print(f"- deepseek_model: {service.deepseek.config.model}")
            print("- deepseek_api_key: configured (redacted)")
            print(f"- qloo_base_url: {service.qloo.base_url}")
            print("- qloo_api_key: configured (redacted)")

            try:
                result = await service.run(
                    npc_id="mara",
                    state=_state(),
                    message=SMOKE_MESSAGE,
                    conversation=[],
                )
            except AgentError as exc:
                _print_trace(service)
                print(f"FAIL: agent error: {exc.code}")
                return 1

            _print_trace(service)
            print(f"- qloo_evidence_count: {len(result.evidence)}")
            print(f"- reply_received: {'yes' if result.reply else 'no'}")
            print(f"- reply_chars: {len(result.reply)}")

            searches = [
                entry
                for entry in result.tool_trace
                if entry.tool == SEARCH_TOOL
            ]
            if not searches:
                print("FAIL: DeepSeek made no search_cultural_entity tool call.")
                return 1
            if not any(entry.status == "ok" for entry in searches):
                print("FAIL: the Qloo search did not return a real entity.")
                return 1
            if result.tool_calls_executed < 1:
                print("FAIL: no tool call was actually executed.")
                return 1

            print("- tool_call_occurred: yes")
            print("- result: PASS")
            return 0
    finally:
        await service.aclose()


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("FAIL: interrupted")
        return 130
    except Exception as exc:
        # Never print arbitrary provider messages, which may contain content
        # or credentials. The exception class is enough for an operator.
        print(f"FAIL: unexpected {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
