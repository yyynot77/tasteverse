"""Application-level wiring for the DeepSeek dialogue agent.

The service owns the two outbound clients so FastAPI can create it lazily (and
optionally inject a mocked one in tests). It contains no game-rule logic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.agents.deepseek_client import DeepSeekClient
from app.agents.orchestrator import AgentRunResult, DialogueAgent
from app.core.config import DeepSeekConfig
from app.models.dialogue import DialogueTurn
from app.models.game import GameState, NpcId
from app.services.qloo_service import QlooClient


@dataclass
class DialogueService:
    """Owns a DeepSeek client and a Qloo client for one application."""

    deepseek: DeepSeekClient
    qloo: QlooClient
    agent: DialogueAgent

    @classmethod
    def create(
        cls,
        *,
        deepseek: DeepSeekClient,
        qloo: QlooClient,
    ) -> "DialogueService":
        agent = DialogueAgent(deepseek=deepseek, qloo=qloo)
        return cls(deepseek=deepseek, qloo=qloo, agent=agent)

    @classmethod
    def from_env(cls) -> "DialogueService":
        """Build from local environment/dotenv without exposing secret values."""

        config = DeepSeekConfig.from_env()
        qloo = QlooClient.from_env()
        deepseek = DeepSeekClient(config)
        return cls.create(deepseek=deepseek, qloo=qloo)

    async def run(
        self,
        *,
        npc_id: NpcId,
        state: GameState,
        message: str,
        conversation: list[DialogueTurn],
    ) -> AgentRunResult:
        return await self.agent.run(
            state=state,
            npc_id=npc_id,
            message=message,
            conversation=conversation,
        )

    async def aclose(self) -> None:
        """Close both owned HTTP clients, tolerating partial teardown."""

        await asyncio.gather(
            self.deepseek.aclose(),
            self.qloo.aclose(),
            return_exceptions=True,
        )


__all__ = ["DialogueService"]
