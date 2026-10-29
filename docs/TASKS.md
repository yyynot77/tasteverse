# Delivery queue

| ID | Priority | Scope | Depends on | Status |
| --- | --- | --- | --- | --- |
| 01 | P0 | Initialize React/Vite/TypeScript/Tailwind/Phaser and FastAPI/Pydantic/httpx/Pytest/Vitest | none | PASS `0052946` |
| 02 | P0 | Qloo client and credentialed smoke test | 01 | Ready for DeepSeek; preliminary live chain passed |
| 03 | P0 | Phaser map and three NPCs | 01 | Queued |
| 04 | P0 | FastAPI base routes and schemas | 01 | Queued |
| 05 | P0 | DeepSeek tool calling and Qloo tools | 02, 04, key | Queued |
| 06 | P0 | Game state and deterministic rules | 04 | Queued |
| 07 | P0 | Plan editor, scoring, endings | 03, 05, 06 | Queued |
| 08 | P0 | Deploy and end to end acceptance | 07, user service access | Queued |

P1 polish follows only after the P0 loop works. P2 scope is deferred.
