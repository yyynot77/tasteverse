# TasteVerse

TasteVerse is a cultural adventure game scaffold. React owns the menus and UI,
Phaser 3 owns the town scene, and FastAPI is the backend.

This repository now includes **Task 03**: a playable pixel-style town scene.
React owns the menus and interaction panel, Phaser 3 owns movement, collision,
and NPC proximity, and a typed event bridge connects the two. Qloo, DeepSeek,
dialogue generation, game rules, scoring, and deployment are **not** implemented
yet. The only application endpoint is `GET /health`.

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

## Scope guard

Task 03 is client-side only: it does not call Qloo or DeepSeek, does not generate
dialogue, and does not add game rules or scoring. NPC interaction is exposed as a
typed event so later API-backed dialogue can sit behind that boundary. Do not add
real API keys to source files, environment examples, or the frontend bundle.

## License

MIT. See [LICENSE](LICENSE).
