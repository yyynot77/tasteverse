# TasteVerse

TasteVerse is a cultural adventure game scaffold. React owns the menus and UI,
Phaser 3 owns the town scene, and FastAPI is the backend.

This repository now includes **Task 04**: typed FastAPI foundation routes for
the fixed NPC catalog and new game sessions. React owns the menus and
interaction panel, Phaser 3 owns movement, collision, and NPC proximity, and a
typed event bridge connects the two. Qloo, DeepSeek, dialogue generation, plan
evaluation, scoring, and deployment are **not** implemented yet.

## Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 3, Phaser 3 |
| Frontend tests | Vitest, Testing Library, jsdom |
| Backend | Python 3.11+, FastAPI, Pydantic, httpx, Uvicorn |
| Backend tests | Pytest |

## Prerequisites

- Node.js 20.19+ or 22.12+ and npm
- Python 3.11+

No `.env` file or API keys are needed for this task. Never commit secrets;
root `.env.example` documents the variables that later tasks will require.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The start screen is visible immediately, and the
960×540 Phaser town scene is ready in the preview panel.

### Town controls

| Input | Action |
| --- | --- |
| `W` `A` `S` `D` or arrow keys | Move the player |
| `E` or `Enter` | Talk to a nearby resident |
| `Escape` or **Close conversation** | Close the NPC panel and resume movement |

The market square has three named residents with fixed locations and distinct
pixel-art appearances: Mara the baker, Jun the record shop owner, and Theo the
town storyteller. World edges, buildings, the fountain, the market stall, crates,
trees, and the bench are solid. Walk close to a resident to see the proximity
prompt, then press `E` or `Enter` to open the React interaction panel.

### Tests and production build

Run the tests and production build:

```powershell
cd frontend
npm test
npm run build
npm run preview
```

- `npm test` runs the Vitest suite once, including interaction-bridge routing,
  movement/collision helpers, NPC proximity, panel open/close, and cleanup.
- `npm run build` type-checks with TypeScript and writes the production bundle
  to `frontend/dist`.
- `npm run preview` serves the built bundle locally.

## Backend

From a fresh checkout:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

On macOS/Linux, activate the environment with:

```bash
source .venv/bin/activate
```

Check the running service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

or:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Run the backend tests:

```powershell
cd backend
python -m pytest
```

## Project layout

```text
frontend/
  src/App.tsx                       Shell, controls copy, interaction panel state
  src/game/PhaserStage.tsx          Phaser 3 game lifecycle and cleanup
  src/game/events.ts                Typed React–Phaser event bridge
  src/game/npcs.ts                  Three fixed NPC definitions
  src/game/world.ts                 Map bounds, obstacles, movement/collision
  src/game/scenes/TownScene.ts      Code-drawn town, player, NPC interactions
  src/game/NpcInteractionPanel.tsx  React NPC interaction dialog
  src/game/*.test.ts                Bridge, movement, and NPC tests
  src/App.test.tsx                  Rendering, panel, and cleanup tests
backend/
  app/main.py                     FastAPI app, lifespan, GET /health
  tests/test_health.py            Pytest health test
docs/                             Product and task documentation
```

## API

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/health` | `{"status":"ok"}` |
| `GET` | `/api/npcs` | Array of the three fixed NPC profiles |
| `GET` | `/api/npcs/{npc_id}` | One NPC profile, or a `404` error envelope |
| `POST` | `/api/game/start` | `{"state": GameState, "state_token": string}` |
| `POST` | `/api/npc/{npc_id}/dialogue` | Reply, real Qloo evidence, rules transition, `state`, `state_token` |
| `POST` | `/api/plan/evaluate` | Evidence, component/NPC reasons, reactions, score, ending, `state`, `state_token` |

`POST /api/game/start` accepts only player-supplied interests:

```json
{
  "player_interests": {
    "movies": ["Inception"],
    "music": ["jazz"],
    "food": ["ramen"]
  }
}
```

All three interest lists are required, but at least one item across them must
be non-empty. Each list holds up to 5 items, each item is trimmed and limited to
80 characters, and unknown fields are rejected. The returned `GameState` starts
at stage `explore` with identical NPC relationship values, empty clues, and
`null` plan, score, and ending. Starting a game performs no Qloo or LLM call.

### Signed state

Every returned `state` is paired with a `state_token`. Mutating routes require
both `state` and `state_token` from the previous response. The token is an
HMAC-SHA256 signature over the full state, session ID, and monotonic
`state_version`; changing a relationship, stage, clue, score, ending, or any
other field invalidates it. Forged state is rejected with `409` and
`state_integrity_error` before any provider or rules call. Persist and resend
both values to resume; do not try to rebuild the token client-side.

Set `GAME_STATE_SECRET` to a stable random value of at least 32 characters in
deployment. Local development without it uses a fixed non-production fallback
so a saved game survives an API restart. A production environment (`APP_ENV` or
`ENVIRONMENT=production`) refuses to start with a missing/short secret.

### Plan evaluation

```json
{
  "state": { "...": "previous GameState" },
  "state_token": "v1...",
  "plan": {
    "movie": "Inception",
    "music": "jazz",
    "food": "ramen",
    "free_text": "optional player description"
  }
}
```

At least one selection or non-empty `free_text` is required. When free text is
needed to fill blank fields, DeepSeek returns advisory movie/music/food labels.
That output is strictly validated; it cannot set a score, ending, or any state
field. Qloo search/insights/tags supply actual entity or tag IDs, linked
deterministically to plan components and NPCs. The Task 06 rules engine alone
computes score and ending. Empty evidence is a valid conservative outcome with
`evidence_status: "unavailable"`; provider failures never substitute invented
entities, and a free-text-only interpretation failure returns a retryable `503`.

Invalid requests and unknown NPCs use one error envelope:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Request validation failed.",
    "retryable": false
  }
}
```

CORS is enabled only for the explicit origins in `CORS_ALLOWED_ORIGINS`
(comma-separated). It defaults to `http://localhost:5173` and
`http://127.0.0.1:5173`; wildcard origins are rejected.

## Scope guard

Task 03 is client-side only: it does not call Qloo or DeepSeek, does not generate
dialogue, and does not add game rules or scoring. NPC interaction is exposed as a
typed event so later API-backed dialogue can sit behind that boundary. Do not add
real API keys to source files, environment examples, or the frontend bundle.

## License

MIT. See [LICENSE](LICENSE).
