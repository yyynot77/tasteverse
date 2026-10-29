# Delivery queue

| ID | Priority | Scope | Depends on | Status |
| --- | --- | --- | --- | --- |
| 01 | P0 | Initialize React/Vite/TypeScript/Tailwind/Phaser and FastAPI/Pydantic/httpx/Pytest/Vitest | none | PASS `0052946` |
| 02 | P0 | Qloo client and credentialed smoke test | 01 | PASS `5df33c4`; 35 tests and live smoke |
| 03 | P0 | Phaser map and three NPCs | 01 | PASS `1676ba4`; browser canvas, movement, and all NPC interactions verified 2026-10-29 |
| 04 | P0 | FastAPI base routes and schemas | 01 | PASS `42ed162`; 75 backend tests |
| 05 | P0 | DeepSeek tool calling and Qloo tools | 02, 04, key | PASS `4396be3`; 115 tests and live tool call |
| 06 | P0 | Game state and deterministic rules | 04 | PASS `6f2060a`; 97 backend tests |
| 07 | P0 | Plan editor, scoring, endings | 03, 05, 06 | PASS 07A `a27ebad`, 07B `f0243a7`; 43 frontend tests/build and live browser E2E verified 2026-10-29 |
| 08 | P0 | Deploy and end to end acceptance | 07, user service access | Queued |

P1 polish follows only after the P0 loop works. P2 scope is deferred.

## Browser acceptance (2026-10-29)

With the local FastAPI and Vite servers running, entered movie/music/food
interests, moved through the Phaser town, spoke to Theo, Mara, and Jun, and saw
real Qloo evidence in each dialogue. The third conversation unlocked the plan.
Submitted a movie/music/food plan and received the backend-selected **Mixed
Night** ending, score **61/100**, and a 12-item evidence ledger. Reloading the
page resumed the same signed ending at state version 4. No user-visible error or
broken flow was observed during this run. Public deployment remains Task 08.
