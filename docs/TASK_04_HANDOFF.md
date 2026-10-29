# DeepSeek Harness handoff — Task 04

## Objective

Add real FastAPI foundation routes and typed schemas for a new game session. Keep dialogue, plan evaluation, Qloo calls, and scoring for later tasks; do not provide success shaped placeholders for them.

## Allowed files

`backend/app/main.py`, new `backend/app/api/**`, `backend/app/models/**`, `backend/tests/**`, and backend config/dependency files only if essential. README may be updated for endpoint documentation. Do not edit frontend, Qloo service, `.env`, or `docs/**`.

## Required API

- Preserve `GET /health` exactly.
- `GET /api/npcs` returns the three fixed NPC IDs/names/roles matching `frontend/src/game/npcs.ts`: `mara` / Mara / Baker; `jun` / Jun / Record shop owner; `theo` / Theo / Town storyteller. Profiles may contain distinct stable personality and cultural interest metadata for later prompts. Do not expose private system prompts.
- `POST /api/game/start` accepts `{ "player_interests": { "movies": string[], "music": string[], "food": string[] } }` and returns `{ "state": GameState }`. Require at least one total interest, bound list and string lengths, trim whitespace, reject unknown fields and malformed input. Return a fresh initial state each time with three NPC relationship values initialized identically, empty clues, stage `explore`, no plan/score/ending. No LLM/Qloo call yet.
- Define Pydantic request/response models that Task 05–07 can extend without arbitrary `dict[str, Any]` state. Distinguish user supplied state from server computed fields. Keep implementation modest.
- Provide a consistent JSON error envelope for invalid input and unknown NPCs, with `code`, `message`, and `retryable`; avoid sensitive internals.
- Configure CORS via explicit environment variable for local Vite origin, not wildcard with credentials.

## Verification

Pytest: health, NPC IDs, valid start, fresh independent state, validation boundaries, error envelope, and CORS origin behavior. Also start Uvicorn and exercise the new routes over HTTP. Run existing Qloo tests to ensure no regression. Report commands/results and known issues. Commit if possible; if the DSH MCP sandbox cannot write `.git`, leave changes for Codex to inspect and commit.
