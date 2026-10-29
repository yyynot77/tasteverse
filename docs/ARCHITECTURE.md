# Architecture

React owns menus, dialogue, task status, plan editing, and endings. Phaser 3 owns town movement, collision, and proximity interactions. React and Phaser share a typed game event bridge. Client localStorage stores resumable progress; the backend validates consequential state transitions and recomputes scores.

FastAPI exposes game, dialogue, and plan routes. A lightweight DeepSeek tool calling loop may invoke allowlisted server tools with validated arguments and a fixed call budget. Qloo integration uses an httpx async client with bounded timeouts, retries on transient failures only, normalized entities, private memory cache, and redacted traces. The server returns evidence provenance separately from LLM prose. The deterministic rules engine alone updates relationship values, event score, and ending.

No database or large Agent framework is required for the demo. Secrets remain in backend environment variables. Errors become typed API responses and recoverable UI states.

## Sequence

Player input → FastAPI validation → DeepSeek tool request → authorized Qloo query → normalized evidence → DeepSeek explanation → rules engine transition → validated state response → UI.
