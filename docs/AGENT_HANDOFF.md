# DeepSeek Harness handoff — Task 01

## Objective

Create the smallest runnable frontend and backend scaffold for TasteVerse. This is a standalone task; do not implement Qloo, DeepSeek, game rules, or deploy yet.

## Allowed files

`frontend/**`, `backend/**`, root `README.md`, root `LICENSE`, root package tooling if needed, and `.gitignore` only to add missing generated paths. Treat `docs/**` and `.env.example` as Codex owned; propose changes separately.

## Required implementation

- React + TypeScript + Vite + Tailwind + Phaser 3 frontend, with a simple visible start screen and an initialized Phaser scene placeholder.
- Python 3.11+ FastAPI + Pydantic + httpx backend, with `GET /health` returning `{ "status": "ok" }`.
- Pytest health test and Vitest smoke test for frontend startup/rendering.
- Example commands for local startup and tests in README.
- Keep secrets out of source and browser bundles. Do not create a real `.env`.

## Required verification

Run frontend install, test, and production build; install backend dependencies and run Pytest; start backend briefly and request `/health`. Report exact commands and results.

## Acceptance

Fresh checkout setup works, the frontend build passes, backend health works, and tests pass. No placeholder pretends to call Qloo or DeepSeek. No unrelated features or large framework added.

## Delivery

Commit with message `task-01: initialize TasteVerse scaffold`. Report changed files, verification output summary, known issues, and commit hash. Codex will inspect the diff and independently rerun checks before PASS.

No direct DeepSeek Harness transport is exposed to Codex yet. This file is the task dispatch artifact until its MCP bridge is available.
