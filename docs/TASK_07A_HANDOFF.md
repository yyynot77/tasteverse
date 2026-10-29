# DeepSeek Harness handoff — Task 07A (backend game loop)

## Objective

Complete the backend side of the main quest: server-authoritative game progress, plan submission, real cultural evidence, deterministic scoring, and three endings. Task 07B will connect the UI.

## Allowed files

`backend/app/**`, `backend/tests/**`, `backend/scripts/**`, backend dependency/config, and README API notes. Do not edit frontend, docs, or `.env`. No database or large agent framework.

## Critical state authority fix

Current dialogue accepts a client-supplied `GameState` and applies rules to it. A client can forge relationships, clues, stage, or score. Implement a small stateless signed state envelope (HMAC with server secret from environment) or a bounded server-owned session store. The server must reject forged computed fields on dialogue and plan routes. Preserve a fresh game start and localStorage resume where practical. If using signatures, include session/version and verify before every mutation; configure a stable secret for deployment with a local-only development fallback. Never expose the secret. Tests must demonstrate a tampered score/relationship/stage is rejected.

## Plan evaluation

- Implement `POST /api/plan/evaluate` with the plan model from `docs/API_CONTRACT.md`; accept movie/music/food selections and optional free text. Bound lengths and reject empty plans.
- Interpret free text with DeepSeek into structured plan fields when needed, with server validation. Model prose or any numeric score is advisory. Handle timeout, malformed JSON, and unavailable provider without fabricating a result.
- Resolve plan terms to real Qloo IDs through search; use Insights/tags as supported to find cultural signals related to the three distinct NPC profiles and player interests. Never use invented `urn:entity:music` or `urn:entity:food_and_drink`. Build `CulturalEvidence` only from actual Qloo responses and link it to a plan component and NPC with a documented deterministic matching rule. Avoid giving all NPCs the same evidence merely because one query returned data.
- Call Task 06 `evaluate_plan` for score and ending. Return structured evidence, per-component/per-NPC reasons, score, ending, and NPC reactions. Do not let LLM directly set state.
- Maintain API error envelope. Missing evidence should produce a conservative valid outcome with clear unavailable status; provider failure should be recoverable rather than hanging.

## Acceptance

Run full Pytest suite. Add tests for forged state rejection, valid dialogue/start/plan flow, real evidence mapping, empty Qloo response, three reachable endings, different preferences producing different scores, provider errors, and idempotence. Add a safe opt-in live end-to-end backend smoke proving DeepSeek, Qloo, and rules all execute; print only counts/status and do not emit keys or raw responses. Report files, test results, live result, known limitations, and commit hash. If DSH cannot write `.git`, leave files for Codex to inspect and commit.
