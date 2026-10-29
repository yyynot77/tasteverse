# Delivery queue

| ID | Priority | Scope | Depends on | Status |
| --- | --- | --- | --- | --- |
| 01 | P0 | Initialize React/Vite/TypeScript/Tailwind/Phaser and FastAPI/Pydantic/httpx/Pytest/Vitest | none | PASS `0052946` |
| 02 | P0 | Qloo client and credentialed smoke test | 01 | PASS `5df33c4`; 35 tests and live smoke |
| 03 | P0 | Phaser map and three NPCs | 01 | PASS code/tests/build `1676ba4`; browser canvas check pending |
| 04 | P0 | FastAPI base routes and schemas | 01 | PASS `42ed162`; 75 backend tests |
| 05 | P0 | DeepSeek tool calling and Qloo tools | 02, 04, key | Ready for DeepSeek; key configured locally |
| 06 | P0 | Game state and deterministic rules | 04 | PASS `6f2060a`; 97 backend tests |
| 07 | P0 | Plan editor, scoring, endings | 03, 05, 06 | Queued |
| 08 | P0 | Deploy and end to end acceptance | 07, user service access | Queued |

P1 polish follows only after the P0 loop works. P2 scope is deferred.
