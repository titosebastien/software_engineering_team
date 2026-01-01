"""
Orchestrator for managing the multi-agent software development lifecycle.

The orchestrator is the "brain" that coordinates all agents, manages state transitions,
validates deliverables, and ensures the project progresses correctly.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.state_machine import StateMachine, ProjectState
from communication.event_bus import EventBus
from communication.schemas import (
    Message,
    MessageType,
    DeliverableMessage,
    ClarificationMessage,
    ErrorMessage,
    StateChangeMessage,
    create_task_message,
)
from memory.adr_manager import ADRManager, ADRStatus
from memory.artifact_store import ArtifactStore


logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orchestrator that manages the multi-agent development workflow.

    Responsibilities:
    - Manage project state transitions
    - Assign tasks to agents
    - Validate deliverables
    - Enforce governance rules
    - Escalate to human when needed
    """

    def __init__(
        self,
        event_bus: EventBus,
        adr_manager: ADRManager,
        artifact_store: ArtifactStore
    ):
        """
        Initialize orchestrator.

        Args:
            event_bus: Communication bus
            adr_manager: ADR manager
            artifact_store: Artifact store
        """
        self.event_bus = event_bus
        self.adr_manager = adr_manager
        self.artifact_store = artifact_store

        # State management
        self.state_machine = StateMachine()

        # Project tracking
        self.project_idea: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.deliverables_received: Dict[str, List[str]] = {}
        self.blockers: List[Dict[str, Any]] = []

        # Runtime state
        self.is_running = False
        self.waiting_for_response = False
        self.current_agent: Optional[str] = None

        logger.info("Orchestrator initialized")

    async def start_project(self, idea: str) -> None:
        """
        Start a new project with an idea.

        Args:
            idea: Project idea description
        """
        self.project_idea = idea
        self.start_time = datetime.utcnow()

        logger.info(f"Starting new project: {idea[:100]}...")

        # Reset state
        self.state_machine.reset()
        self.deliverables_received.clear()
        self.blockers.clear()

        # Transition to ANALYSIS
        self._transition_to_state(ProjectState.ANALYSIS)

        # Assign task to analyst
        await self._assign_task_for_current_state()

    async def run(self) -> None:
        """
        Run the orchestrator's main loop.

        Listens for messages from agents and manages the workflow.
        """
        self.is_running = True
        logger.info("Orchestrator started")

        try:
            async for message in self.event_bus.listen("orchestrator"):
                if not self.is_running:
                    break

                await self._handle_message(message)

        except asyncio.CancelledError:
            logger.info("Orchestrator cancelled")
            raise
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)

    async def stop(self) -> None:
        """Stop the orchestrator."""
        self.is_running = False
        logger.info("Orchestrator stopped")

    async def _handle_message(self, message: Message) -> None:
        """
        Handle incoming message.

        Args:
            message: Received message
        """
        logger.debug(f"Orchestrator received: type={message.type}, from={message.from_agent}")

        try:
            if message.type == MessageType.DELIVERABLE:
                await self._handle_deliverable(message)
            elif message.type == MessageType.CLARIFICATION:
                await self._handle_clarification(message)
            elif message.type == MessageType.ERROR:
                await self._handle_error(message)
            elif message.type == MessageType.STATUS:
                await self._handle_status(message)
            else:
                logger.warning(f"Unhandled message type: {message.type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _handle_deliverable(self, message: DeliverableMessage) -> None:
        """
        Handle deliverable submission from an agent.

        Args:
            message: Deliverable message
        """
        agent = message.from_agent
        artifacts = message.content.get("artifacts", [])
        summary = message.content.get("summary", "")

        logger.info(f"Received deliverable from {agent}: {summary}")

        # Track deliverables
        current_state = self.state_machine.current_state
        if current_state not in self.deliverables_received:
            self.deliverables_received[current_state] = []

        self.deliverables_received[current_state].extend(artifacts)

        # Validate deliverables
        if await self._validate_deliverables(current_state):
            logger.info(f"Deliverables validated for state: {current_state}")

            # Handle special cases
            if current_state == ProjectState.ARCHITECTURE:
                # Process proposed ADRs
                await self._process_proposed_adrs()

            elif current_state == ProjectState.REVIEW:
                # Check CTO review decision
                await self._process_cto_review(message)
                return  # CTO review handles its own transitions

            # Transition to next state
            await self._advance_to_next_state()

        else:
            logger.warning(f"Deliverables incomplete for state: {current_state}")
            # Could request re-work here

    async def _handle_clarification(self, message: ClarificationMessage) -> None:
        """
        Handle clarification request.

        For now, log it. In a full implementation, this would escalate to human.

        Args:
            message: Clarification message
        """
        question = message.content.get("question", "")
        context = message.content.get("context", "")

        logger.warning(
            f"CLARIFICATION NEEDED from {message.from_agent}:\n"
            f"Question: {question}\n"
            f"Context: {context}"
        )

        # Add to blockers
        self.blockers.append({
            "type": "clarification",
            "from": message.from_agent,
            "question": question,
            "context": context,
            "blocking": message.blocking
        })

        # In production, this would escalate to human
        # For now, we'll just log it

    async def _handle_error(self, message: ErrorMessage) -> None:
        """
        Handle error notification.

        Args:
            message: Error message
        """
        error_type = message.content.get("error_type", "unknown")
        error_msg = message.content.get("message", "")

        logger.error(
            f"ERROR from {message.from_agent} ({error_type}): {error_msg}"
        )

        # Add to blockers
        self.blockers.append({
            "type": "error",
            "from": message.from_agent,
            "error_type": error_type,
            "message": error_msg
        })

        # Critical errors might require human intervention or project restart

    async def _handle_status(self, message: Message) -> None:
        """
        Handle status update.

        Args:
            message: Status message
        """
        status = message.content.get("status", "")
        logger.info(f"Status from {message.from_agent}: {status}")

    def _transition_to_state(self, new_state: ProjectState) -> bool:
        """
        Transition to a new state and broadcast the change.

        Args:
            new_state: Target state

        Returns:
            True if successful
        """
        old_state = self.state_machine.current_state

        if self.state_machine.transition_to(new_state):
            logger.info(f"State transition: {old_state} -> {new_state}")

            # Broadcast state change
            asyncio.create_task(self._broadcast_state_change(old_state, new_state))

            return True

        return False

    async def _broadcast_state_change(
        self,
        old_state: ProjectState,
        new_state: ProjectState
    ) -> None:
        """
        Broadcast state change to all agents.

        Args:
            old_state: Previous state
            new_state: New state
        """
        message = StateChangeMessage(
            from_agent="orchestrator",
            content={
                "old_state": old_state.value,
                "new_state": new_state.value,
                "progress": self.state_machine.get_progress_percentage()
            }
        )

        await self.event_bus.broadcast(message)

    async def _assign_task_for_current_state(self) -> None:
        """Assign task to the appropriate agent for current state."""
        current_state = self.state_machine.current_state
        agent = self.state_machine.get_responsible_agent(current_state)

        # Build task description based on state
        task_description = self._build_task_description(current_state)

        # Send task message
        task_message = create_task_message(
            from_agent="orchestrator",
            to_agent=agent,
            description=task_description,
            additional_data={
                "state": current_state.value,
                "project_idea": self.project_idea
            }
        )

        await self.event_bus.send(task_message)

        self.current_agent = agent

        logger.info(f"Assigned {current_state.value} task to {agent}")

    def _build_task_description(self, state: ProjectState) -> str:
        """
        Build task description for a state.

        Args:
            state: Current state

        Returns:
            Task description
        """
        descriptions = {
            ProjectState.ANALYSIS: (
                f"Analyze the following project idea and produce functional specifications "
                f"and user stories:\n\n{self.project_idea}"
            ),
            ProjectState.ARCHITECTURE: (
                "Design the system architecture based on the functional specifications. "
                "Create architecture documentation, API specifications, and ADRs."
            ),
            ProjectState.DESIGN: (
                "Create UI/UX design including design system, wireframes, and UX guidelines "
                "based on the user stories and functional requirements."
            ),
            ProjectState.IMPLEMENTATION: (
                "Implement the backend and frontend according to the architecture and design specifications."
            ),
            ProjectState.TESTING: (
                "Test the implemented system against all user stories and functional requirements. "
                "Report any bugs and verify quality."
            ),
            ProjectState.REVIEW: (
                "Perform comprehensive CTO-level review of the entire system including "
                "architecture, security, code quality, and operational readiness."
            ),
        }

        return descriptions.get(state, f"Execute {state.value} phase")

    async def _validate_deliverables(self, state: ProjectState) -> bool:
        """
        Validate that required deliverables are present for a state.

        Args:
            state: State to validate

        Returns:
            True if all required deliverables present
        """
        required = self.state_machine.get_required_deliverables(state)

        if not required:
            return True  # No deliverables required

        received = self.deliverables_received.get(state, [])

        # Check if all required artifacts exist
        missing = []
        for req in required:
            # Check in received list or artifact store
            if req not in received and not self.artifact_store.exists(req):
                missing.append(req)

        if missing:
            logger.warning(f"Missing deliverables for {state}: {missing}")
            return False

        logger.info(f"All deliverables present for {state}")
        return True

    async def _process_proposed_adrs(self) -> None:
        """Process ADRs proposed by architect."""
        # In a full implementation, this might require human approval
        # For now, auto-accept proposed ADRs

        proposed_adrs = self.adr_manager.list_by_status(ADRStatus.PROPOSED)

        for adr in proposed_adrs:
            logger.info(f"Auto-accepting ADR: {adr.id} - {adr.title}")
            self.adr_manager.accept_adr(adr.id)

    async def _process_cto_review(self, message: DeliverableMessage) -> None:
        """
        Process CTO review results.

        Args:
            message: Review deliverable message
        """
        decision = message.content.get("decision", "")
        score = message.content.get("score", 0)

        logger.info(f"CTO Review: decision={decision}, score={score}")

        if decision == "GO":
            # Advance to delivery
            await self._advance_to_next_state()
        elif decision == "CONDITIONAL GO":
            # Could implement conditional logic here
            logger.warning("Conditional GO received - advancing anyway for now")
            await self._advance_to_next_state()
        else:  # NO-GO
            # Need to go back and fix issues
            logger.error(f"CTO Review NO-GO (score={score})")
            # In production, would determine which state to return to
            self._transition_to_state(ProjectState.IMPLEMENTATION)
            await self._assign_task_for_current_state()

    async def _advance_to_next_state(self) -> None:
        """Advance to the next state in the workflow."""
        next_state = self.state_machine.get_next_state()

        if next_state is None:
            logger.info("Reached terminal state")
            return

        self._transition_to_state(next_state)

        # Assign task for new state
        await self._assign_task_for_current_state()

    def get_project_status(self) -> Dict[str, Any]:
        """
        Get current project status.

        Returns:
            Status dictionary
        """
        return {
            "state": self.state_machine.current_state.value,
            "progress": self.state_machine.get_progress_percentage(),
            "current_agent": self.current_agent,
            "deliverables_count": sum(len(d) for d in self.deliverables_received.values()),
            "blockers": len(self.blockers),
            "runtime_seconds": (
                (datetime.utcnow() - self.start_time).total_seconds()
                if self.start_time
                else 0
            )
        }
