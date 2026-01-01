"""
Project state machine.

This module defines the states and transitions for the software development lifecycle.
"""

from enum import Enum
from typing import Dict, List, Optional
import logging


logger = logging.getLogger(__name__)


class ProjectState(str, Enum):
    """States in the software development lifecycle."""

    IDEA = "idea"                      # Initial idea
    ANALYSIS = "analysis"              # Requirements analysis
    ARCHITECTURE = "architecture"      # Architecture design
    DESIGN = "design"                  # UI/UX design
    IMPLEMENTATION = "implementation"  # Code implementation
    TESTING = "testing"                # QA testing
    REVIEW = "review"                  # CTO review
    DELIVERY = "delivery"              # Ready for delivery
    FAILED = "failed"                  # Project failed (unrecoverable)


class StateMachine:
    """
    Manages project state transitions.

    Ensures that the project progresses through states in the correct order
    and that all required deliverables are present before transitioning.
    """

    # Define valid state transitions
    TRANSITIONS: Dict[ProjectState, List[ProjectState]] = {
        ProjectState.IDEA: [ProjectState.ANALYSIS],
        ProjectState.ANALYSIS: [ProjectState.ARCHITECTURE, ProjectState.FAILED],
        ProjectState.ARCHITECTURE: [ProjectState.DESIGN, ProjectState.ANALYSIS, ProjectState.FAILED],
        ProjectState.DESIGN: [ProjectState.IMPLEMENTATION, ProjectState.ARCHITECTURE, ProjectState.FAILED],
        ProjectState.IMPLEMENTATION: [ProjectState.TESTING, ProjectState.DESIGN, ProjectState.FAILED],
        ProjectState.TESTING: [ProjectState.REVIEW, ProjectState.IMPLEMENTATION, ProjectState.FAILED],
        ProjectState.REVIEW: [ProjectState.DELIVERY, ProjectState.IMPLEMENTATION, ProjectState.FAILED],
        ProjectState.DELIVERY: [],  # Terminal state
        ProjectState.FAILED: [],    # Terminal state
    }

    # Agent responsible for each state
    STATE_AGENT_MAP: Dict[ProjectState, str] = {
        ProjectState.IDEA: "orchestrator",
        ProjectState.ANALYSIS: "analyst",
        ProjectState.ARCHITECTURE: "architect",
        ProjectState.DESIGN: "designer",
        ProjectState.IMPLEMENTATION: "backend",  # Backend is primary, frontend runs concurrently
        ProjectState.TESTING: "qa",
        ProjectState.REVIEW: "cto",
        ProjectState.DELIVERY: "orchestrator",
        ProjectState.FAILED: "orchestrator",
    }

    # Required deliverables for each state transition
    REQUIRED_DELIVERABLES: Dict[ProjectState, List[str]] = {
        ProjectState.ANALYSIS: ["functional_spec.md", "user_stories.yaml"],
        ProjectState.ARCHITECTURE: ["architecture.md", "openapi.yaml", "decisions.md"],
        ProjectState.DESIGN: ["design_system.md", "wireframes.md"],
        ProjectState.IMPLEMENTATION: ["backend_code", "frontend_code"],
        ProjectState.TESTING: ["test_plan.md", "test_results.md"],
        ProjectState.REVIEW: ["cto_review.md"],
        ProjectState.DELIVERY: [],
    }

    def __init__(self, initial_state: ProjectState = ProjectState.IDEA):
        """
        Initialize state machine.

        Args:
            initial_state: Starting state
        """
        self.current_state = initial_state
        self.state_history: List[ProjectState] = [initial_state]

        logger.info(f"State machine initialized at state: {initial_state}")

    def can_transition_to(self, target_state: ProjectState) -> bool:
        """
        Check if transition to target state is valid from current state.

        Args:
            target_state: Desired state

        Returns:
            True if transition is valid
        """
        valid_next_states = self.TRANSITIONS.get(self.current_state, [])
        return target_state in valid_next_states

    def transition_to(self, target_state: ProjectState) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            target_state: State to transition to

        Returns:
            True if transition successful, False otherwise
        """
        if not self.can_transition_to(target_state):
            logger.warning(
                f"Invalid transition: {self.current_state} -> {target_state}. "
                f"Valid states: {self.TRANSITIONS.get(self.current_state, [])}"
            )
            return False

        old_state = self.current_state
        self.current_state = target_state
        self.state_history.append(target_state)

        logger.info(f"State transition: {old_state} -> {target_state}")

        return True

    def get_next_state(self) -> Optional[ProjectState]:
        """
        Get the next state in the normal workflow.

        Returns:
            Next state or None if at terminal state
        """
        workflow_order = [
            ProjectState.IDEA,
            ProjectState.ANALYSIS,
            ProjectState.ARCHITECTURE,
            ProjectState.DESIGN,
            ProjectState.IMPLEMENTATION,
            ProjectState.TESTING,
            ProjectState.REVIEW,
            ProjectState.DELIVERY,
        ]

        try:
            current_idx = workflow_order.index(self.current_state)
            if current_idx < len(workflow_order) - 1:
                return workflow_order[current_idx + 1]
        except ValueError:
            pass

        return None

    def get_responsible_agent(self, state: Optional[ProjectState] = None) -> str:
        """
        Get the agent responsible for a state.

        Args:
            state: State to query (defaults to current state)

        Returns:
            Agent name
        """
        state = state or self.current_state
        return self.STATE_AGENT_MAP.get(state, "orchestrator")

    def get_required_deliverables(self, state: Optional[ProjectState] = None) -> List[str]:
        """
        Get required deliverables for completing a state.

        Args:
            state: State to query (defaults to current state)

        Returns:
            List of required deliverable names
        """
        state = state or self.current_state
        return self.REQUIRED_DELIVERABLES.get(state, [])

    def is_terminal_state(self, state: Optional[ProjectState] = None) -> bool:
        """
        Check if state is terminal (no further transitions).

        Args:
            state: State to check (defaults to current state)

        Returns:
            True if terminal
        """
        state = state or self.current_state
        return state in [ProjectState.DELIVERY, ProjectState.FAILED]

    def reset(self) -> None:
        """Reset to initial state."""
        self.current_state = ProjectState.IDEA
        self.state_history = [ProjectState.IDEA]
        logger.info("State machine reset to IDEA")

    def get_progress_percentage(self) -> float:
        """
        Get rough progress percentage based on current state.

        Returns:
            Progress as percentage (0-100)
        """
        state_weights = {
            ProjectState.IDEA: 0,
            ProjectState.ANALYSIS: 10,
            ProjectState.ARCHITECTURE: 25,
            ProjectState.DESIGN: 40,
            ProjectState.IMPLEMENTATION: 70,
            ProjectState.TESTING: 85,
            ProjectState.REVIEW: 95,
            ProjectState.DELIVERY: 100,
            ProjectState.FAILED: 0,
        }

        return state_weights.get(self.current_state, 0)
