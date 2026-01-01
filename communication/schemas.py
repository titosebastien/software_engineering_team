"""
Message schemas for inter-agent communication.

This module defines the structure of messages exchanged between agents
via the event bus, ensuring consistent and structured communication.
"""

from enum import Enum
from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages that can be sent between agents."""

    TASK = "task"                    # Assign a task to an agent
    DELIVERABLE = "deliverable"      # Agent submits completed work
    CLARIFICATION = "clarification"  # Request for clarification
    QUESTION = "question"            # Ask a question
    STATUS = "status"                # Status update
    ERROR = "error"                  # Error notification
    REVIEW_REQUEST = "review_request"  # Request a review
    REVIEW_COMPLETE = "review_complete"  # Review completed
    STATE_CHANGE = "state_change"    # Project state changed
    BROADCAST = "broadcast"          # Broadcast to all agents


class MessagePriority(str, Enum):
    """Priority levels for messages."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    """
    Base message structure for agent communication.

    All messages sent via the event bus must follow this structure.
    """

    # Required fields
    from_agent: str = Field(..., description="Sender agent name")
    to_agent: str = Field(..., description="Recipient agent name or 'orchestrator'")
    type: MessageType = Field(..., description="Type of message")
    content: Dict[str, Any] = Field(default_factory=dict, description="Message payload")

    # Optional fields
    blocking: bool = Field(
        default=False,
        description="Whether this message blocks sender's progress"
    )
    priority: MessagePriority = Field(
        default=MessagePriority.MEDIUM,
        description="Message priority"
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="ID to correlate related messages"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When message was created"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskMessage(Message):
    """Message for assigning a task to an agent."""

    type: MessageType = Field(default=MessageType.TASK, const=True)

    def __init__(self, **data):
        """Ensure content has required task fields."""
        super().__init__(**data)
        # Validate task content structure
        required = ["description"]
        for field in required:
            if field not in self.content:
                raise ValueError(f"Task message must have '{field}' in content")


class DeliverableMessage(Message):
    """Message for submitting completed work."""

    type: MessageType = Field(default=MessageType.DELIVERABLE, const=True)

    def __init__(self, **data):
        """Ensure content has required deliverable fields."""
        super().__init__(**data)
        # Validate deliverable content
        required = ["summary", "artifacts"]
        for field in required:
            if field not in self.content:
                raise ValueError(f"Deliverable message must have '{field}' in content")


class ClarificationMessage(Message):
    """Message for requesting clarification."""

    type: MessageType = Field(default=MessageType.CLARIFICATION, const=True)
    blocking: bool = Field(default=True)  # Clarifications usually block progress

    def __init__(self, **data):
        """Ensure content has required clarification fields."""
        super().__init__(**data)
        required = ["question", "context"]
        for field in required:
            if field not in self.content:
                raise ValueError(f"Clarification message must have '{field}' in content")


class StatusMessage(Message):
    """Message for status updates."""

    type: MessageType = Field(default=MessageType.STATUS, const=True)


class ErrorMessage(Message):
    """Message for error notifications."""

    type: MessageType = Field(default=MessageType.ERROR, const=True)
    priority: MessagePriority = Field(default=MessagePriority.HIGH)

    def __init__(self, **data):
        """Ensure content has required error fields."""
        super().__init__(**data)
        required = ["error_type", "message"]
        for field in required:
            if field not in self.content:
                raise ValueError(f"Error message must have '{field}' in content")


class StateChangeMessage(Message):
    """Message for project state changes."""

    type: MessageType = Field(default=MessageType.STATE_CHANGE, const=True)
    to_agent: str = Field(default="broadcast")  # State changes broadcast to all

    def __init__(self, **data):
        """Ensure content has required state change fields."""
        super().__init__(**data)
        required = ["old_state", "new_state"]
        for field in required:
            if field not in self.content:
                raise ValueError(f"State change message must have '{field}' in content")


# Helper functions for creating messages

def create_task_message(
    from_agent: str,
    to_agent: str,
    description: str,
    additional_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> TaskMessage:
    """
    Create a task assignment message.

    Args:
        from_agent: Sender (usually 'orchestrator')
        to_agent: Recipient agent
        description: Task description
        additional_data: Additional task data
        **kwargs: Additional message fields

    Returns:
        TaskMessage instance
    """
    content = {"description": description}
    if additional_data:
        content.update(additional_data)

    return TaskMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        content=content,
        **kwargs
    )


def create_deliverable_message(
    from_agent: str,
    to_agent: str,
    summary: str,
    artifacts: list[str],
    additional_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> DeliverableMessage:
    """
    Create a deliverable submission message.

    Args:
        from_agent: Agent submitting work
        to_agent: Recipient (usually 'orchestrator')
        summary: Summary of deliverables
        artifacts: List of artifact file paths
        additional_data: Additional deliverable data
        **kwargs: Additional message fields

    Returns:
        DeliverableMessage instance
    """
    content = {
        "summary": summary,
        "artifacts": artifacts
    }
    if additional_data:
        content.update(additional_data)

    return DeliverableMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        content=content,
        **kwargs
    )


def create_clarification_message(
    from_agent: str,
    to_agent: str,
    question: str,
    context: str,
    options: Optional[list[str]] = None,
    **kwargs
) -> ClarificationMessage:
    """
    Create a clarification request message.

    Args:
        from_agent: Agent asking for clarification
        to_agent: Agent who can provide clarification
        question: The question
        context: Context for the question
        options: Optional list of possible answers
        **kwargs: Additional message fields

    Returns:
        ClarificationMessage instance
    """
    content = {
        "question": question,
        "context": context
    }
    if options:
        content["options"] = options

    return ClarificationMessage(
        from_agent=from_agent,
        to_agent=to_agent,
        content=content,
        **kwargs
    )
