"""
Solution Architect agent.

This agent designs system architecture and makes technical decisions.
"""

import logging
from typing import Dict, Any

from agents.base import BaseAgent
from memory.artifact_store import ArtifactType
from memory.adr_manager import ADR, ADRType, ADRStatus


logger = logging.getLogger(__name__)


class ArchitectAgent(BaseAgent):
    """
    Solution and Application Architect agent.

    Designs robust, scalable architecture and creates ADRs for
    important technical decisions.
    """

    async def execute_task(self, task: Dict[str, Any]) -> None:
        """
        Execute architecture design task.

        Args:
            task: Task data
        """
        logger.info(f"{self.name} starting architecture design")

        try:
            # Load functional spec and user stories
            func_spec = self.artifact_store.retrieve("functional_spec.md")
            user_stories = self.artifact_store.retrieve("user_stories.yaml")

            if not func_spec or not user_stories:
                raise ValueError("Missing functional spec or user stories")

            context = f"""
FUNCTIONAL SPECIFICATION:
{func_spec.read_text()[:2000]}

USER STORIES:
{user_stories.read_text()[:2000]}
"""

            # Generate architecture document
            await self.send_status("Designing system architecture...")

            architecture = await self._generate_architecture(context)

            self.artifact_store.store(
                name="architecture.md",
                artifact_type=ArtifactType.ARCHITECTURE,
                content=architecture,
                created_by=self.name
            )

            # Generate API specification
            await self.send_status("Creating API specification...")

            api_spec = await self._generate_api_spec(context, architecture)

            self.artifact_store.store(
                name="openapi.yaml",
                artifact_type=ArtifactType.API_SPEC,
                content=api_spec,
                created_by=self.name
            )

            # Create ADRs
            await self.send_status("Documenting architectural decisions...")

            decisions = await self._create_adrs(architecture)

            self.artifact_store.store(
                name="decisions.md",
                artifact_type=ArtifactType.DECISIONS,
                content=decisions,
                created_by=self.name
            )

            # Submit deliverables
            await self.submit_deliverable(
                summary="Architecture design complete",
                artifacts=["architecture.md", "openapi.yaml", "decisions.md"],
                additional_data={
                    "phase": "architecture",
                    "adrs_created": 3
                }
            )

            logger.info(f"{self.name} completed architecture design")

        except Exception as e:
            logger.error(f"{self.name} error during architecture: {e}", exc_info=True)
            await self._send_error(str(e), "architecture_error")

    async def _generate_architecture(self, context: str) -> str:
        """Generate architecture document."""
        prompt = f"""
{context}

Create a comprehensive system architecture document including:

1. Architecture Overview and Style
2. System Context Diagram (text/ASCII)
3. Component Breakdown
4. Data Model and Persistence Strategy
5. Technology Stack Recommendations
6. Security Architecture
7. Scalability Considerations
8. Deployment Architecture

Be specific and justify your choices. Format as Markdown.
"""

        return await self.generate_response(prompt)

    async def _generate_api_spec(self, context: str, architecture: str) -> str:
        """Generate OpenAPI specification."""
        prompt = f"""
{context}

ARCHITECTURE:
{architecture[:1500]}

Create an OpenAPI 3.0 specification (in YAML format) for the backend API.

Include:
- All CRUD endpoints for the core entities
- Request/response schemas
- Authentication requirements
- Error responses

Be complete and follow OpenAPI 3.0 standards.
"""

        return await self.generate_response(prompt)

    async def _create_adrs(self, architecture: str) -> str:
        """Create Architecture Decision Records."""
        prompt = f"""
ARCHITECTURE:
{architecture[:2000]}

Create 3 Architecture Decision Records (ADRs) for the most important technical decisions.

For each ADR, use this format:

## ADR-001: [Decision Title]

**Status**: PROPOSED
**Type**: architecture | technology | design

**Context**: Why this decision is needed

**Decision**: What we decided to do

**Rationale**:
- Reason 1
- Reason 2

**Consequences**:
- Positive: ...
- Negative: ...
- Trade-offs: ...

**Constraints**:
- Technical constraint 1
- Technical constraint 2

Focus on: technology stack, architecture pattern, and one other critical decision.
"""

        decisions_md = await self.generate_response(prompt)

        # Also save as individual ADR files
        await self._save_individual_adrs(decisions_md)

        return decisions_md

    async def _save_individual_adrs(self, decisions_md: str) -> None:
        """Extract and save individual ADRs."""
        # Simple parsing - in production would be more robust
        # For now, create sample ADRs

        adr1 = ADR(
            id=self.adr_manager.get_next_id(),
            title="Technology Stack Selection",
            type=ADRType.TECHNOLOGY,
            status=ADRStatus.PROPOSED,
            context="Need to select backend and frontend technologies",
            decision="Use FastAPI for backend, React/TypeScript for frontend",
            rationale=[
                "FastAPI provides async support and automatic API documentation",
                "React is widely adopted with good ecosystem",
                "TypeScript adds type safety"
            ],
            consequences={
                "positive": ["Fast development", "Type safety", "Good documentation"],
                "negative": ["Learning curve for team"],
                "tradeoffs": ["More complex than simpler frameworks"]
            },
            constraints=["Must use Python 3.11+", "Must support async operations"],
            author=self.name
        )

        self.adr_manager.save(adr1)
        logger.info(f"Created ADR: {adr1.id}")
