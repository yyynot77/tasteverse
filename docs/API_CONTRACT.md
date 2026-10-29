# API contract draft (v1)

All application routes use JSON. Error: `{ "error": { "code": string, "message": string, "retryable": boolean } }`. Do not return secrets, raw Qloo payloads, or tool arguments containing keys.

| Route | Request | Response |
| --- | --- | --- |
| `GET /health` | none | `{ "status": "ok" }` |
| `POST /api/game/start` | `{ "player_interests": { "movies": string[], "music": string[], "food": string[] } }` | `{ "state": GameState }` |
| `POST /api/npc/{npc_id}/dialogue` | `{ "state": GameState, "message": string }` | `{ "reply": string, "clues": Clue[], "evidence": Evidence[], "state": GameState }` |
| `POST /api/plan/evaluate` | `{ "state": GameState, "plan": { "movie": string, "music": string, "food": string, "free_text": string } }` | `{ "analysis": string, "evidence": Evidence[], "score": number, "ending": string, "state": GameState }` |

`GameState` contains player interests, task stage, three NPC relationship values, discovered clues, optional plan, cultural match values, score, and optional ending. Backend owns numeric transitions. `Evidence` contains source `qloo`, source entity ID, normalized label, query type, and any usable signal. Empty evidence remains empty and must not be replaced with invented entities.

## External Qloo contract

Base URL `https://hackathon.api.qloo.com`; authentication header `X-Api-Key`. Use `GET /search` to obtain real entity IDs, then `GET /v2/insights` with `filter.type` and supported query parameters. `GET /v2/tags` is optional. Search `types` and insights `filter.type` are distinct. Never infer an entity ID from its label. Exact query combinations and response shape require confirmation against the live official guide and a credentialed smoke test before implementation is accepted.
