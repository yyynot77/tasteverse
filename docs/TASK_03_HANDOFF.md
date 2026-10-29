# DeepSeek Harness handoff — Task 03

## Objective

Replace the Task 01 Phaser placeholder with one playable pixel-style town scene. A player must move with keyboard controls, encounter collision boundaries/obstacles, approach three distinct NPCs, and trigger an interaction event that React can consume. Keep this task client-side; dialogue generation and game rules come later.

## Allowed files

`frontend/src/game/**`, related frontend UI/types/tests, `frontend/package.json` only if essential, and README instructions for controls. Do not edit backend, `.env`, or `docs/**`.

## Required behavior

- Render one coherent full town map at the existing 960×540 scene size, using original code-drawn pixel shapes or repository-local assets. No external image hotlinks.
- Player moves with WASD and arrow keys; diagonal speed is normalized. World boundaries and at least two visible obstacles block movement.
- Exactly three named NPCs have visibly different appearance and fixed locations. Interact only in proximity with E or Enter; show an on-screen proximity prompt.
- Emit a typed event with NPC ID/name through a React–Phaser bridge. React displays a lightweight NPC interaction panel, and closing it restores movement. Keep future API integration behind the event boundary.
- Scene and listeners are cleaned up on unmount/remount. Avoid duplicate games/listeners under React Strict Mode.
- Provide accessible React copy for movement and interaction controls; allow keyboard dismissal of panel.

## Tests and acceptance

Run Vitest and production build. Add meaningful tests for typed interaction event routing and panel open/close, plus any isolated movement/collision logic that can be tested without mocking all of Phaser internals. Codex will independently inspect code, run tests/build, and manually verify the rendered interaction if possible.

No Qloo/DeepSeek success claims are expected from this task. Report changed files, exact checks/results, known issues, and commit hash. If DSH cannot write `.git/index.lock`, leave files uncommitted for Codex to inspect and commit.
