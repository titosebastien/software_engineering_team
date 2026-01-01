"""
Base agent class.

This module provides the base class that all specialized agents inherit from.
It handles common functionality like LLM interaction, memory access, and communication.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from llm.base import BaseLLM
from llm.factory import create_llm_for_role
from llm.prompt_loader import PromptLoader
from memory.adr_manager import ADRManager, ADR
from memory.artifact_store import ArtifactStore
from communication.event_bus import EventBus
from communication.schemas import (
    Message,
    TaskMessage,
    DeliverableMessage,
    ClarificationMessage,
    StatusMessage,
    ErrorMessage,
    create_deliverable_message,
    create_clarification_message,
)


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all AI agents in the system.

    This provides common functionality for:
    - Loading prompts
    - Interacting with LLMs
    - Accessing memory (ADRs and artifacts)
    - Communicating via event bus
    - Handling tasks
    """

    def __init__(
        self,
        name: str,
        role: str,
        event_bus: EventBus,
        adr_manager: ADRManager,
        artifact_store: ArtifactStore,
        llm: Optional[BaseLLM] = None
    ):
        """
        Initialize base agent.

        Args:
            name: Unique agent name (e.g., "analyst_1")
            role: Agent role (e.g., "analyst", "architect")
            event_bus: Communication bus
            adr_manager: Architecture decision manager
            artifact_store: Artifact storage
            llm: Optional LLM instance (creates one if not provided)
        """
        self.name = name
        self.role = role
        self.event_bus = event_bus
        self.adr_manager = adr_manager
        self.artifact_store = artifact_store

        # Load prompts
        self.prompt_loader = PromptLoader()
        self.system_prompt = self._load_system_prompt()

        # Initialize LLM
        self.llm = llm or create_llm_for_role(role)

        # State
        self.current_task: Optional[Dict[str, Any]] = None
        self.is_running = False

        logger.info(f"Agent initialized: {name} (role={role})")

    def _load_system_prompt(self) -> str:
        """
        Load system prompt for this agent's role.

        Returns:
            Combined system prompt
        """
        return self.prompt_loader.load_for_role(self.role, include_global=True)

    async def start(self) -> None:
        """
        Start the agent's main loop.

        The agent will listen for messages and process tasks.
        """
        self.is_running = True
        logger.info(f"Agent {self.name} started")

        try:
            async for message in self.event_bus.listen(self.name):
                if not self.is_running:
                    break

                await self._handle_message(message)

        except asyncio.CancelledError:
            logger.info(f"Agent {self.name} cancelled")
            raise
        except Exception as e:
            logger.error(f"Agent {self.name} error: {e}", exc_info=True)
            await self._send_error(str(e))

    async def stop(self) -> None:
        """Stop the agent."""
        self.is_running = False
        logger.info(f"Agent {self.name} stopped")

    async def _handle_message(self, message: Message) -> None:
        """
        Handle incoming message.

        Args:
            message: Received message
        """
        logger.debug(f"{self.name} received message: type={message.type}")

        try:
            if isinstance(message, TaskMessage):
                await self._handle_task(message)
            elif isinstance(message, ClarificationMessage):
                await self._handle_clarification(message)
            else:
                logger.warning(f"Unhandled message type: {message.type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await self._send_error(str(e), context=message.dict())

    async def _handle_task(self, message: TaskMessage) -> None:
        """
        Handle task assignment.

        Args:
            message: Task message
        """
        logger.info(f"{self.name} received task: {message.content.get('description', 'N/A')}")

        self.current_task = message.content

        # Execute the task
        await self.execute_task(message.content)

    async def _handle_clarification(self, message: ClarificationMessage) -> None:
        """
        Handle clarification request.

        Args:
            message: Clarification message
        """
        logger.info(f"{self.name} received clarification request")
        # Subclasses can override to handle clarifications
        pass

    @abstractmethod
    async def execute_task(self, task: Dict[str, Any]) -> None:
        """
        Execute a task.

        This must be implemented by each specialized agent.

        Args:
            task: Task data
        """
        pass

    async def generate_response(
        self,
        user_prompt: str,
        context: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            user_prompt: User's request
            context: Additional context to include
            temperature: Override default temperature

        Returns:
            Generated response
        """
        # Add ADR context
        adrs = self.adr_manager.list_accepted()
        adr_context = self._format_adrs_for_prompt(adrs)

        # Combine contexts
        full_user_prompt = f"""
{user_prompt}

---

ARCHITECTURAL CONSTRAINTS (MUST RESPECT):
{adr_context}
"""

        if context:
            full_user_prompt += f"\n\nADDITIONAL CONTEXT:\n{context}"

        # Generate
        response = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=full_user_prompt,
            temperature=temperature or 0.0
        )

        return response

    def _format_adrs_for_prompt(self, adrs: list[ADR]) -> str:
        """
        Format ADRs for inclusion in prompt.

        Args:
            adrs: List of ADRs

        Returns:
            Formatted string
        """
        if not adrs:
            return "No architectural decisions yet."

        formatted = []
        for adr in adrs:
            formatted.append(f"""
{adr.id}: {adr.title}
- Decision: {adr.decision}
- Constraints: {', '.join(adr.constraints) if adr.constraints else 'None'}
""")

        return "\n".join(formatted)

    async def submit_deliverable(
        self,
        summary: str,
        artifacts: list[str],
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Submit completed work to orchestrator.

        Args:
            summary: Summary of deliverables
            artifacts: List of artifact file names
            additional_data: Additional data to include
        """
        message = create_deliverable_message(
            from_agent=self.name,
            to_agent="orchestrator",
            summary=summary,
            artifacts=artifacts,
            additional_data=additional_data
        )

        await self.event_bus.send(message)

        logger.info(f"{self.name} submitted deliverable: {summary}")

    async def request_clarification(
        self,
        to_agent: str,
        question: str,
        context: str,
        options: Optional[list[str]] = None
    ) -> None:
        """
        Request clarification from another agent or human.

        Args:
            to_agent: Who to ask
            question: The question
            context: Context for the question
            options: Optional list of possible answers
        """
        message = create_clarification_message(
            from_agent=self.name,
            to_agent=to_agent,
            question=question,
            context=context,
            options=options
        )

        await self.event_bus.send(message)

        logger.info(f"{self.name} requested clarification from {to_agent}")

    async def send_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Send status update to orchestrator.

        Args:
            status: Status message
            details: Additional details
        """
        message = StatusMessage(
            from_agent=self.name,
            to_agent="orchestrator",
            content={"status": status, **(details or {})}
        )

        await self.event_bus.send(message)

    async def _send_error(
        self,
        error_msg: str,
        error_type: str = "execution_error",
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send error notification.

        Args:
            error_msg: Error message
            error_type: Type of error
            context: Additional context
        """
        message = ErrorMessage(
            from_agent=self.name,
            to_agent="orchestrator",
            content={
                "error_type": error_type,
                "message": error_msg,
                "context": context or {}
            }
        )

        await self.event_bus.send(message)

        logger.error(f"{self.name} sent error: {error_msg}")
