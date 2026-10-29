# Acceptance gates

Each task is accepted only after independent diff review and relevant commands run by Codex. Status is PASS, REWORK with specific findings, or BLOCKED with evidence.

## Final P0 gate

- Frontend builds and FastAPI starts.
- A credentialed smoke test searches a real Qloo entity and uses its returned ID in Insights, with redacted output and honest empty/error behavior.
- DeepSeek actually issues a validated Qloo tool call during a game interaction.
- Three NPCs can be approached and spoken to; one map and the full main quest are playable.
- Distinct interest and plan inputs cause distinct deterministic outcomes; all three endings can be triggered by tests.
- Recoverable API failures do not strand the game.
- No secret is shipped to the frontend or committed; README, license, deployment instructions, and a publicly playable demo exist.
