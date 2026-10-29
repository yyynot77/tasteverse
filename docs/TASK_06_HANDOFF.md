# DeepSeek Harness handoff — Task 06

## Objective

Build a deterministic, testable game rules engine. Keep LLM prose and Qloo evidence outside the scoring authority. The engine must yield repeatable relationship, stage, score, and ending transitions from explicit inputs.

## Allowed files

`backend/app/core/**`, `backend/app/models/game.py`, new focused backend tests, and imports in backend API only if needed. Do not edit frontend, Qloo client, `.env`, or `docs/**`. Do not implement DeepSeek or placeholder Qloo responses.

## Rules contract

- Define explicit pure functions for recording an NPC clue/interacted NPC, updating that NPC relationship, and evaluating a submitted plan from verified backend-provided cultural evidence. An event must not be countable twice; validate NPC IDs, clue ownership, and stage prerequisites.
- Keep numeric thresholds and weights as named constants. Bound relationships and score to 0–100. Do not use randomness, wall-clock time, or LLM-provided scores.
- Plan evaluation must use structured evidence with provenance (`qloo` entity/tag IDs and the linked plan component/NPC) plus completion state. It must not treat natural-language rationale as evidence or accept arbitrary client supplied numeric match values as authoritative. If evidence is missing or empty, score conservatively and mark it unavailable; never invent a Qloo success.
- Derive exactly three stable endings: `perfect_harmony`, `mixed_night`, `cultural_chaos`. Define reachable, transparent thresholds so tests can trigger each ending with different verified evidence and relationship states.
- Produce a typed transition result with explainable component and NPC scores/reasons suitable for a UI, while keeping prose generation for Task 05/07.
- Extend `GameStage` and `GameState` models only as needed. Do not change Task 04 start API response semantics.

## Tests and acceptance

Cover initial state compatibility, NPC transition/idempotence, prerequisite validation, relationship bounds, empty evidence behavior, repeatability, score bounds, and deterministic reachability of all three endings. Test different input evidence producing different outcomes. Run complete backend Pytest suite and report results. If DSH cannot write `.git`, leave files for Codex to inspect and commit.
