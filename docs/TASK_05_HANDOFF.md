# DeepSeek Harness handoff — Task 05

## Objective

Implement a small DeepSeek Agent orchestrator that actually executes authorized Qloo tool calls for NPC dialogue and cultural exploration. Do not let model output mutate score, relationship, stage, or ending. Task 06 rules remain sole authority.

## Allowed files

`backend/app/agents/**`, `backend/app/api/**`, relevant backend models, backend tests, backend dependency/config files if essential, and a safe standalone live smoke script. Do not modify Qloo client except a narrowly justified bug fix. Do not edit frontend or docs. Do not read or print secret values in logs or reports; use existing local `backend/.env` through configuration.

## API and orchestrator

- Implement `POST /api/npc/{npc_id}/dialogue` with bounded user message length, validated NPC ID, bounded conversation context, and a typed response separating natural language reply, actual Qloo evidence, tool trace metadata, and any rule-engine transition. Preserve compatibility with Task 04 start state and Task 06 rules.
- Use DeepSeek `POST https://api.deepseek.com/chat/completions`, model `deepseek-flash`, `Authorization: Bearer`, `tools` function schema, and validate every generated tool argument server-side. Follow current official docs: https://api-docs.deepseek.com/api/create-chat-completion/ and https://api-docs.deepseek.com/guides/tool_calls/.
- Allowlist tools: `search_cultural_entity`, `get_cultural_insights`, `get_npc_profile`, `get_game_context`. Qloo tools must execute only through the existing Qloo client, with real returned IDs. The first two tools may return normalized, bounded Qloo data. Context/profile tools return server-owned data only.
- Bound tool calls, response size, context size, timeout, and retry behavior. Handle malformed tool JSON, unknown tool, empty Qloo results, rate limits, and DeepSeek errors as typed recoverable failures. Do not echo external error bodies or credentials.
- NPC prompts should be distinct and aware of the main quest. Keep prompt injection from tool results or user messages from overriding server policy. No framework required.
- No fake Qloo evidence, synthetic success trace, or LLM-decided game score. Persist or return only client-safe conversation context.

## Verification

- Mocked transport tests must demonstrate real tool dispatch and proper assistant/tool message cycle, authorization/validation, empty result behavior, bounded calls, and secret redaction.
- Add an opt-in live smoke that makes an actual DeepSeek tool call leading to Qloo search and reports only safe counts/status. Use a small token limit and one bounded run. Clearly fail if no tool call occurs; do not call it PASS on a plain-text answer.
- Run full Pytest and the live smoke. Report exact output summary, files, limitations, and commit hash. DSH may leave files uncommitted if `.git` is not writable; Codex will independently inspect and commit accepted work.
