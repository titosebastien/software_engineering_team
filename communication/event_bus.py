"""
Async event bus for inter-agent communication.

This module provides an in-memory event bus for agents to communicate
using structured messages. It supports both direct messaging and broadcasting.
"""

import asyncio
import logging
from typing import AsyncIterator, Dict, List, Optional, Set
from collections import defaultdict
from datetime import datetime

from communication.schemas import Message, MessageType


logger = logging.getLogger(__name__)


class EventBus:
    """
    Asynchronous event bus for agent communication.

    This provides a structured communication channel where agents can send
    messages to each other through named channels (queues).
    """

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the event bus.

        Args:
            max_queue_size: Maximum number of messages per queue
        """
        # Message queues for each agent/channel
        self._queues: Dict[str, asyncio.Queue[Message]] = {}

        # Subscribers for broadcast messages
        self._subscribers: Set[str] = set()

        # Message history for debugging
        self._history: List[Message] = []
        self._max_history = 100

        # Statistics
        self._stats = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_agent": defaultdict(int)
        }

        self.max_queue_size = max_queue_size

        logger.info("Event bus initialized")

    def _get_queue(self, agent_name: str) -> asyncio.Queue[Message]:
        """
        Get or create a queue for an agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Queue for the agent
        """
        if agent_name not in self._queues:
            self._queues[agent_name] = asyncio.Queue(maxsize=self.max_queue_size)
            logger.debug(f"Created queue for agent: {agent_name}")

        return self._queues[agent_name]

    async def send(
        self,
        message: Message,
        store_in_history: bool = True
    ) -> None:
        """
        Send a message to a specific agent.

        Args:
            message: Message to send
            store_in_history: Whether to store in message history

        Raises:
            asyncio.QueueFull: If recipient queue is full
        """
        # Handle broadcast messages
        if message.to_agent == "broadcast" or message.type == MessageType.BROADCAST:
            await self.broadcast(message, store_in_history)
            return

        # Get recipient queue
        queue = self._get_queue(message.to_agent)

        try:
            # Add to queue
            await queue.put(message)

            # Update statistics
            self._stats["total_messages"] += 1
            self._stats["messages_by_type"][message.type] += 1
            self._stats["messages_by_agent"][message.from_agent] += 1

            # Store in history
            if store_in_history:
                self._history.append(message)
                if len(self._history) > self._max_history:
                    self._history.pop(0)

            logger.debug(
                f"Message sent: {message.from_agent} -> {message.to_agent} "
                f"(type={message.type}, blocking={message.blocking})"
            )

        except asyncio.QueueFull:
            logger.error(
                f"Queue full for agent {message.to_agent}. "
                f"Message from {message.from_agent} dropped."
            )
            raise

    async def receive(self, agent_name: str) -> Message:
        """
        Receive one message from an agent's queue.

        This is a blocking call that waits for a message to arrive.

        Args:
            agent_name: Name of the agent receiving messages

        Returns:
            Received message
        """
        queue = self._get_queue(agent_name)
        message = await queue.get()

        logger.debug(
            f"Message received by {agent_name}: "
            f"from={message.from_agent}, type={message.type}"
        )

        return message

    async def listen(self, agent_name: str) -> AsyncIterator[Message]:
        """
        Listen for messages continuously (async generator).

        This yields messages as they arrive, allowing agents to process
        them in a continuous loop.

        Args:
            agent_name: Name of the agent listening

        Yields:
            Messages as they arrive

        Example:
            async for message in bus.listen("analyst"):
                await process_message(message)
        """
        # Register as subscriber for broadcasts
        self._subscribers.add(agent_name)

        logger.info(f"Agent {agent_name} started listening for messages")

        try:
            while True:
                message = await self.receive(agent_name)
                yield message

        except asyncio.CancelledError:
            logger.info(f"Agent {agent_name} stopped listening")
            self._subscribers.discard(agent_name)
            raise

    async def broadcast(
        self,
        message: Message,
        store_in_history: bool = True
    ) -> None:
        """
        Broadcast a message to all subscribed agents.

        Args:
            message: Message to broadcast
            store_in_history: Whether to store in history
        """
        message.to_agent = "broadcast"

        # Send to all subscribers
        for subscriber in self._subscribers:
            # Don't send back to sender
            if subscriber != message.from_agent:
                try:
                    queue = self._get_queue(subscriber)
                    await queue.put(message)

                except asyncio.QueueFull:
                    logger.warning(
                        f"Could not broadcast to {subscriber}: queue full"
                    )

        # Update statistics
        self._stats["total_messages"] += len(self._subscribers)
        self._stats["messages_by_type"][message.type] += 1
        self._stats["messages_by_agent"][message.from_agent] += 1

        # Store in history
        if store_in_history:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        logger.debug(
            f"Broadcast from {message.from_agent} "
            f"to {len(self._subscribers)} subscribers"
        )

    def get_queue_size(self, agent_name: str) -> int:
        """
        Get the current size of an agent's queue.

        Args:
            agent_name: Name of the agent

        Returns:
            Number of messages in queue
        """
        if agent_name not in self._queues:
            return 0

        return self._queues[agent_name].qsize()

    def get_history(
        self,
        limit: Optional[int] = None,
        filter_type: Optional[MessageType] = None,
        filter_agent: Optional[str] = None
    ) -> List[Message]:
        """
        Get message history.

        Args:
            limit: Maximum number of messages to return
            filter_type: Filter by message type
            filter_agent: Filter by sender agent

        Returns:
            List of historical messages
        """
        history = self._history.copy()

        # Apply filters
        if filter_type:
            history = [m for m in history if m.type == filter_type]

        if filter_agent:
            history = [m for m in history if m.from_agent == filter_agent]

        # Apply limit
        if limit:
            history = history[-limit:]

        return history

    def get_stats(self) -> Dict:
        """
        Get event bus statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_messages": self._stats["total_messages"],
            "messages_by_type": dict(self._stats["messages_by_type"]),
            "messages_by_agent": dict(self._stats["messages_by_agent"]),
            "active_queues": len(self._queues),
            "subscribers": list(self._subscribers),
            "queue_sizes": {
                name: queue.qsize()
                for name, queue in self._queues.items()
            }
        }

    def clear_history(self) -> None:
        """Clear message history."""
        self._history.clear()
        logger.info("Message history cleared")

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_agent": defaultdict(int)
        }
        logger.info("Statistics reset")
