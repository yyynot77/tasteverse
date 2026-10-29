"""Live Qloo smoke test.

This script uses the local ``backend/.env`` credentials (or process environment)
to search for a real movie, then feeds the returned entity ID into Insights. It
prints only safe status/count information; the API key and entity ID are never
printed.

Run from ``backend``:

    python -m scripts.qloo_smoke

or:

    python scripts/qloo_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.qloo_service import (  # noqa: E402
    QlooClient,
    QlooError,
    QlooEntity,
)

SEARCH_QUERY = "Inception"
ENTITY_TYPE = "urn:entity:movie"
TAKE = 5


def _select_entity(entities: list[QlooEntity]) -> QlooEntity | None:
    for entity in entities:
        if entity.name.strip().casefold() == SEARCH_QUERY.casefold():
            return entity
    return entities[0] if entities else None


async def _run() -> int:
    try:
        client = QlooClient.from_env()
    except QlooError as exc:
        print(f"FAIL: {exc}")
        return 1

    async with client:
        print("Qloo live smoke")
        print(f"- base_url: {client.base_url}")
        print("- api_key: configured (redacted)")

        try:
            matches = await client.search_entities(
                SEARCH_QUERY,
                types=[ENTITY_TYPE],
                take=TAKE,
            )
        except QlooError as exc:
            print(f"FAIL: search error: {exc}")
            return 1

        print(f"- search: {SEARCH_QUERY!r} / {ENTITY_TYPE} -> {len(matches)} entities")
        selected = _select_entity(matches)
        if selected is None:
            print("FAIL: search returned no entities; cannot run insights honestly.")
            return 1

        print("- selected entity: real ID from search (redacted)")
        try:
            insights = await client.get_insights(
                filter_type=ENTITY_TYPE,
                entity_ids=[selected.entity_id],
                take=TAKE,
            )
        except QlooError as exc:
            print(f"FAIL: insights error: {exc}")
            return 1

        print(f"- insights: filter.type={ENTITY_TYPE} -> {len(insights)} entities")
        if not insights:
            print("FAIL: insights returned no entities.")
            return 1

        print("- result: PASS")
        return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except KeyboardInterrupt:
        print("FAIL: interrupted")
        return 130
    except Exception as exc:  # Do not print arbitrary messages that may leak data.
        print(f"FAIL: unexpected {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
