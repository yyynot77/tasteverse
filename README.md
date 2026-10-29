# TasteVerse

TasteVerse is a playable cultural adventure game. React owns the field-journal
UI, Phaser 3 owns the town scene, and FastAPI owns the signed game state,
dialogue, Qloo evidence, and deterministic scoring.

This repository includes the complete frontend loop from **Task 07B**: choose
movie/music/food interests, start a signed game, explore the pixel market
square, talk to all three residents through API-backed dialogue, unlock and
submit a festival plan, and read the server-selected ending. Signed state is
persisted in `localStorage`, so a reload resumes the same session. Qloo
evidence is displayed separately from NPC prose; the browser never calculates a
competing score.

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

No API key belongs in the frontend or its bundle. The frontend only needs the
API origin. Backend provider keys stay in the backend environment; root
`.env.example` documents those variables. Never commit `.env` files.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The start screen asks for at least one movie,
music, or food interest, then calls `POST /api/game/start`. For local
development Vite talks to `http://127.0.0.1:8000` by default. To point at a
different API origin, create `frontend/.env.local`:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Use an absolute HTTPS origin for a deployed or separately hosted API. When
`VITE_API_BASE_URL` is unset, a production build uses same-origin `/api`
requests, so no localhost URL is baked into a deployment bundle. See
`frontend/.env.example`.

### Playable flow

1. Enter interests (up to five per category, comma or newline separated) and
   **Enter the town**. The returned `state` + `state_token` are saved together.
2. Walk up to Mara, Jun, or Theo and press `E`/`Enter`. Send a message in the
   dialogue panel. Real Qloo evidence appears in its own panel beneath the NPC
   reply, with rapport and stage changes from the signed response.
3. Meeting all three residents advances the stage to `plan` and unlocks the
   movie/music/food plan form. Add at least one field or a free-text note.
4. Submit the plan to `POST /api/plan/evaluate`. The UI shows backend evidence
   status, component and NPC reasons, reactions, score, and the ending
   (**Perfect Harmony**, **Mixed Night**, or **Cultural Chaos**).
5. **Start over** clears the saved signed game after an inline confirmation.
   A rejected/stale state offers the same restart path. Network, 401, 402, 429,
   5xx, empty-evidence, and retryable failures are shown inline; closing a
   dialogue panel always restores movement.

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

- `npm test` runs the Vitest suite once. It covers interests/start requests,
  signed-state persistence and resume, all three NPC dialogue routes, progress
  unlock, plan submission, all three backend endings, empty evidence, and
  recoverable network/rate-limit/stale-state failures.
- `npm run build` type-checks with TypeScript and writes the production bundle
  to `frontend/dist`.
- `npm run preview` serves the built bundle locally. Set
  `VITE_API_BASE_URL` before building when the preview should call a separate
  API origin.

For a local end-to-end run, start the backend first (see below), then run
`npm run dev` and walk through the flow in the browser. The browser stores the
signed game under `tasteverse.signed-game.v1` in `localStorage`.

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
  src/App.tsx                       Game shell, signed session, quest orchestration
  src/api/client.ts                 Typed fetch client and API error envelope
  src/api/types.ts                  Wire shapes mirroring backend Pydantic models
  src/api/errors.ts                 Recovery guidance for 401/402/409/429/5xx/network
  src/components/StartScreen.tsx    Interest form and POST /api/game/start
  src/components/QuestJournal.tsx   Resident progress, rapport, and interests
  src/components/DialoguePanel.tsx  API dialogue, Qloo evidence, retry/close recovery
  src/components/PlanPanel.tsx      Plan form, retryable evaluation errors
  src/components/EndingReport.tsx   Server score/ending, evidence, reasons, reactions
  src/game/storage.ts               Signed state + token localStorage persistence
  src/game/interests.ts             Interest validation/parsing for the API
  src/game/PhaserStage.tsx          Phaser 3 game lifecycle and cleanup
  src/game/events.ts                Typed React–Phaser event bridge
  src/game/npcs.ts                  Three fixed NPC definitions
  src/game/world.ts                 Map bounds, obstacles, movement/collision
  src/game/scenes/TownScene.ts      Code-drawn town, player, NPC interactions
  src/game/*.test.ts                Bridge, movement, storage, and NPC tests
  src/api/*.test.ts                 Error/recovery tests
  src/App.test.tsx                  Start, resume, dialogue, plan, ending, error tests
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

The backend is authoritative for signed state transitions, Qloo evidence,
score, and ending. The frontend displays those values and never computes a
competing score or fabricates evidence. `state` and `state_token` must always be
sent and stored together. Do not add real API keys to source files, environment
examples, or the frontend bundle.

## License

MIT. See [LICENSE](LICENSE).
