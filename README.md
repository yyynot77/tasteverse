# TasteVerse

TasteVerse is a cultural adventure game scaffold. React owns the menus and UI,
Phaser 3 owns the town scene, and FastAPI is the backend.

This repository is at **Task 01**: a runnable, deliberately minimal scaffold.
Qloo, DeepSeek, NPCs, game rules, scoring, and deployment are **not**
implemented yet. The only application endpoint is `GET /health`.

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
Phaser `TownScene` placeholder initializes in the preview panel.

Run the smoke tests and production build:

```powershell
cd frontend
npm test
npm run build
npm run preview
```

- `npm test` runs the Vitest suite once.
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
  src/App.tsx                     Start screen and scaffold status
  src/game/PhaserStage.tsx        Phaser 3 game initialization
  src/game/scenes/TownScene.ts    Placeholder scene (no game rules)
  src/App.test.tsx                Vitest startup/rendering smoke tests
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

Task 01 intentionally does not call Qloo or DeepSeek, does not contain game
logic, and does not include deployment configuration. Do not add real API keys
to source files, environment examples, or the frontend bundle.

## License

MIT. See [LICENSE](LICENSE).
