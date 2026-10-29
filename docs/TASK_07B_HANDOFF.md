# DeepSeek Harness handoff — Task 07B (playable frontend loop)

## Objective

Turn the existing Phaser town and backend APIs into one complete browser game. A player must select interests, explore and talk to all three NPCs, submit an event plan, and see a deterministic ending. Make the app playable, responsive, and recoverable when services fail.

## Allowed files

`frontend/**` and README frontend instructions. Do not edit backend, docs, or `.env`. Do not put any API key in frontend code or bundle.

## API flow

- On a new game, collect at least one movie/music/food interest and call `POST /api/game/start`. Persist returned signed `state` and `state_token` in localStorage. On reload, resume them; provide a clear restart action.
- Keep the Task 03 Phaser movement and NPC proximity interaction. On interaction, open a React dialogue panel. Call `POST /api/npc/{npc_id}/dialogue` with signed state, message, and bounded conversation context; update state/token from response. Show real Qloo evidence separately from NPC prose. The player should see progress toward meeting all three residents.
- After stage advances to `plan`, provide movie/music/food fields and optional free text. Call `POST /api/plan/evaluate` with signed state and plan. Show loading, retryable error, evidence status, component/NPC reasons, score, NPC reactions, and the returned ending. Never calculate a competing score on the client.
- Three ending presentations: Perfect Harmony, Mixed Night, Cultural Chaos. The UI may style them differently, but must use backend `ending` and `score`.
- Handle 401/402/429/5xx, network failures, empty evidence, and stale/invalid state token with understandable recovery actions. A recoverable failure must not trap the player in a modal or disable movement permanently.
- Use environment-configured API origin for local Vite and deployment. No hardcoded localhost in production. Keep TypeScript request/response shapes aligned with actual backend models.

## Visual direction

Build on the pixel town as a playful cultural festival field journal: warm parchment, ink and tomato red accents, bold pixel display details, readable body text, purposeful asymmetry, and restrained motion. Avoid generic dashboard cards and unrelated gradients. Prioritize clear quest progress and the map. Respect keyboard focus, reduced motion, and smaller screens.

## Acceptance

Add meaningful Vitest tests for start, signed-state persistence/resume, all three NPC dialogue routing, progress unlock, plan submission, three endings, and recoverable errors. Run `npm test` and `npm run build`. Provide a local dev integration path and perform at least one browser-level walkthrough if possible. Report actual checks, known issues, changed files, and commit hash. DSH may leave files uncommitted if `.git` is not writable; Codex will independently inspect and commit accepted work.
