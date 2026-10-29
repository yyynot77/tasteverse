# Qloo live smoke test — 2026-10-29

Environment: local `backend/.env`, ignored by Git. No API key or raw response is recorded here.

1. `GET https://hackathon.api.qloo.com/search?query=Inception` with `X-Api-Key` returned HTTP 200 and 20 results. A result named `Inception` supplied a real `entity_id`.
2. `GET https://hackathon.api.qloo.com/v2/insights` with `filter.type=urn:entity:movie` and `signal.interests.entities` set to that returned ID returned HTTP 200. Response contained `success` and `results`, with 20 entities.

This verifies authentication and a nonempty search-to-insights chain. It does not yet verify empty responses, 4xx/5xx handling, retries, or the future client implementation. Task 02 must cover those cases.
