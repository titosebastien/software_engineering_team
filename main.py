"""
Main entry point for the AI Software Engineering Team.

This script initializes and runs the multi-agent system.
"""

import asyncio
import logging
import sys
from typing import Optional

from config import get_settings, configure_logging
from communication.event_bus import EventBus
from memory.adr_manager import ADRManager
from memory.artifact_store import ArtifactStore
from core.orchestrator import Orchestrator
from agents.analyst import AnalystAgent
from agents.architect import ArchitectAgent
from agents.cto_reviewer import CTOReviewerAgent
from agents.simple_agents import (
    DesignerAgent,
    BackendAgent,
    FrontendAgent,
    QAAgent
)


logger = logging.getLogger(__name__)


class AITeam:
    """
    Main application class that manages the AI software engineering team.
    """

    def __init__(self):
        """Initialize the AI team."""
        # Load settings
        self.settings = get_settings()
        configure_logging(self.settings)

        logger.info("=" * 80)
        logger.info("AI SOFTWARE ENGINEERING TEAM - STARTING")
        logger.info("=" * 80)

        # Initialize core components
        self.event_bus = EventBus(max_queue_size=self.settings.MAX_QUEUE_SIZE)
        self.adr_manager = ADRManager(adr_dir=self.settings.ARTIFACTS_DIR / "adrs")
        self.artifact_store = ArtifactStore(artifacts_dir=self.settings.ARTIFACTS_DIR)

        # Initialize orchestrator
        self.orchestrator = Orchestrator(
            event_bus=self.event_bus,
            adr_manager=self.adr_manager,
            artifact_store=self.artifact_store
        )

        # Initialize agents
        self.agents = {}
        self._init_agents()

    def _init_agents(self):
        """Initialize all agents."""
        logger.info("Initializing agents...")

        agent_classes = [
            ("analyst", AnalystAgent),
            ("architect", ArchitectAgent),
            ("designer", DesignerAgent),
            ("backend", BackendAgent),
            ("frontend", FrontendAgent),
            ("qa", QAAgent),
            ("cto", CTOReviewerAgent),
        ]

        for role, AgentClass in agent_classes:
            agent = AgentClass(
                name=role,
                role=role,
                event_bus=self.event_bus,
                adr_manager=self.adr_manager,
                artifact_store=self.artifact_store
            )
            self.agents[role] = agent
            logger.info(f"  ✓ {role.capitalize()} agent initialized")

        logger.info(f"Total agents initialized: {len(self.agents)}")

    async def run_project(self, project_idea: str) -> None:
        """
        Run a project from idea to delivery.

        Args:
            project_idea: The project idea/description
        """
        logger.info("=" * 80)
        logger.info("STARTING PROJECT")
        logger.info("=" * 80)
        logger.info(f"Project Idea: {project_idea}")
        logger.info("=" * 80)

        # Start all agents
        agent_tasks = []
        for role, agent in self.agents.items():
            task = asyncio.create_task(agent.start())
            agent_tasks.append(task)
            logger.info(f"Started {role} agent")

        # Start orchestrator
        orchestrator_task = asyncio.create_task(self.orchestrator.run())

        # Small delay to let everything initialize
        await asyncio.sleep(1)

        # Start the project
        await self.orchestrator.start_project(project_idea)

        # Wait for completion or timeout
        try:
            # Set a reasonable timeout (e.g., 30 minutes)
            timeout = 1800

            logger.info(f"Project running (timeout: {timeout}s)...")

            await asyncio.wait_for(
                self._wait_for_completion(orchestrator_task, agent_tasks),
                timeout=timeout
            )

        except asyncio.TimeoutError:
            logger.error("Project execution timeout!")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")

        finally:
            # Stop all agents
            logger.info("Stopping agents...")
            for agent in self.agents.values():
                await agent.stop()

            # Stop orchestrator
            await self.orchestrator.stop()

            # Cancel tasks
            for task in agent_tasks + [orchestrator_task]:
                task.cancel()

            # Wait for cancellation
            await asyncio.gather(*agent_tasks, orchestrator_task, return_exceptions=True)

        # Print final status
        self._print_final_status()

    async def _wait_for_completion(self, orchestrator_task, agent_tasks):
        """Wait for project completion."""
        # In a real implementation, would check for DELIVERY or FAILED state
        # For now, just run until manually stopped or timeout
        await orchestrator_task

    def _print_final_status(self):
        """Print final project status."""
        logger.info("=" * 80)
        logger.info("PROJECT STATUS")
        logger.info("=" * 80)

        status = self.orchestrator.get_project_status()

        logger.info(f"State: {status['state']}")
        logger.info(f"Progress: {status['progress']}%")
        logger.info(f"Current Agent: {status['current_agent']}")
        logger.info(f"Deliverables: {status['deliverables_count']}")
        logger.info(f"Blockers: {status['blockers']}")
        logger.info(f"Runtime: {status['runtime_seconds']:.1f}s")

        logger.info("=" * 80)
        logger.info("Event Bus Statistics:")
        stats = self.event_bus.get_stats()
        logger.info(f"  Total Messages: {stats['total_messages']}")
        logger.info(f"  Active Queues: {stats['active_queues']}")
        logger.info(f"  Subscribers: {stats['subscribers']}")

        logger.info("=" * 80)
        logger.info("Artifacts Created:")
        for artifact in self.artifact_store.list_all():
            logger.info(f"  - {artifact.name} ({artifact.artifact_type.value})")

        logger.info("=" * 80)


async def main():
    """Main entry point."""
    # Get project idea from command line or use default
    if len(sys.argv) > 1:
        project_idea = " ".join(sys.argv[1:])
    else:
        # Default project for testing
        project_idea = """
        Create a simple Todo API application that allows users to:
        - Create, read, update, and delete todo items
        - Mark todos as completed
        - Filter todos by status (completed/pending)
        - Each todo has a title and completion status

        The API should be RESTful with proper HTTP methods and status codes.
        It should include basic input validation and error handling.
        """

    # Create and run the AI team
    team = AITeam()

    try:
        await team.run_project(project_idea)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("AI SOFTWARE ENGINEERING TEAM")
    print("=" * 80 + "\n")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("Session ended")
    print("=" * 80 + "\n")
