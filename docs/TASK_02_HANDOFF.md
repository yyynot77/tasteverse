# DeepSeek Harness handoff — Task 02

## Objective

Implement a small, production usable async Qloo client and a separate live smoke test. A preliminary credentialed search → insights chain passed; see `docs/QLOO_SMOKE.md`.

## Allowed files

`backend/app/services/qloo_service.py`, required `__init__.py`, `backend/tests/test_qloo_service.py`, `backend/scripts/qloo_smoke.py`, and backend dependency/config files only if necessary. Do not modify frontend, game state, or Codex owned `docs/**`. Do not read or print the key value in any report. Do not commit `backend/.env`.

## Requirements

- Use `httpx.AsyncClient`, `QLOO_BASE_URL` and `QLOO_API_KEY` from server environment or local `backend/.env`; never expose secrets in exceptions, logs, return models, or CLI output.
- Implement entity search (`GET /search`), optional tag search (`GET /v2/tags`), and insights (`GET /v2/insights`) with explicit supported `filter.type`, valid parameter validation, timeouts, bounded retry for transient errors, typed errors, normalized results, and private memory cache.
- Keep search `types` separate from insights `filter.type`; use real returned entity IDs for insights. Do not use forbidden paths or fabricate results.
- Tests with mocked HTTP transport must cover success, empty results, 401, 429/5xx retry cap, timeout, malformed response, validation, cache, and redaction.
- Standalone smoke script must use live credentials to search a real movie, feed its returned ID to insights, assert nonempty entities, and report only safe status/count/ID redacted or omitted. It must fail honestly if key is absent or results empty.
- Check exact parameters against the official Qloo guide: https://docs.qloo.com/reference/qloo-llm-hackathon-developer-guide.

## Verification and delivery

Run Pytest and the live smoke script. Return changed files, commands and results, known limitations, and commit hash. If MCP worker cannot write `.git`, leave files uncommitted and report that specific limitation; Codex will inspect and commit accepted work.
