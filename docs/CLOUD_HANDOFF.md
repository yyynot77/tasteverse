# TasteVerse cloud handoff

Repository: `https://github.com/yyynot77/tasteverse` (private), branch `main`.

The local DSH stdio MCP server is installed on the Windows machine and will not exist in Codex Cloud. Cloud tasks should use Codex directly for implementation and acceptance, while following the task contracts in `docs/`.

## Current state

- Tasks 01–06 and 07A are committed and independently tested.
- Task 07B frontend implementation is committed as `f0243a7`; 43 Vitest tests and the production build pass. A real browser walkthrough and live backend integration remain to be accepted.
- Task 08 public deployment and end-to-end acceptance remain open.
- GitHub Actions runs frontend tests/build and backend tests on push and PR without service keys.

## Cloud environment

1. Connect the private GitHub repository to a Codex Cloud environment and enable the package registries plus HTTPS access to `api.deepseek.com` and `hackathon.api.qloo.com` for live integration checks.
2. Install with `cd frontend && npm ci` and `cd backend && python -m pip install -r requirements.txt` if automatic setup does not detect both folders.
3. Configure service credentials in the cloud environment's secret mechanism, never in Git, chat prompts, or setup scripts: `QLOO_API_KEY`, `DEEPSEEK_API_KEY`, `GAME_STATE_SECRET` (stable random value of at least 32 characters). Set `QLOO_BASE_URL=https://hackathon.api.qloo.com` and `APP_ENV=production` only when a production-like environment is ready.
4. Validate with `cd frontend && npm test && npm run build` and `cd backend && python -m pytest -q -p no:cacheprovider`. Run live smokes only when the cloud secret mechanism makes the service keys available to the task and outbound domains are allowed.

The local `backend/.env` is intentionally ignored and is not copied to cloud. A cloud task should never claim a live Qloo/DeepSeek PASS based on mocked tests alone.
