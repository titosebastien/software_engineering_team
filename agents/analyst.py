"""
Functional Analyst agent.

This agent analyzes project ideas and produces functional specifications
and user stories.
"""

import logging
from typing import Dict, Any

from agents.base import BaseAgent
from memory.artifact_store import ArtifactType


logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """
    Functional Analyst agent.

    Transforms raw product ideas into clear functional specifications
    and user stories with acceptance criteria.
    """

    async def execute_task(self, task: Dict[str, Any]) -> None:
        """
        Execute functional analysis task.

        Args:
            task: Task data containing project idea
        """
        logger.info(f"{self.name} starting functional analysis")

        project_idea = task.get("project_idea", task.get("description", ""))

        try:
            # Generate functional specification
            await self.send_status("Generating functional specification...")

            func_spec = await self._generate_functional_spec(project_idea)

            # Store artifact
            self.artifact_store.store(
                name="functional_spec.md",
                artifact_type=ArtifactType.FUNCTIONAL_SPEC,
                content=func_spec,
                created_by=self.name
            )

            # Generate user stories
            await self.send_status("Generating user stories...")

            user_stories = await self._generate_user_stories(project_idea, func_spec)

            # Store artifact
            self.artifact_store.store(
                name="user_stories.yaml",
                artifact_type=ArtifactType.USER_STORIES,
                content=user_stories,
                created_by=self.name
            )

            # Submit deliverables
            await self.submit_deliverable(
                summary="Functional analysis complete",
                artifacts=["functional_spec.md", "user_stories.yaml"],
                additional_data={
                    "phase": "analysis"
                }
            )

            logger.info(f"{self.name} completed functional analysis")

        except Exception as e:
            logger.error(f"{self.name} error during analysis: {e}", exc_info=True)
            await self._send_error(str(e), "analysis_error")

    async def _generate_functional_spec(self, project_idea: str) -> str:
        """
        Generate functional specification.

        Args:
            project_idea: Raw project idea

        Returns:
            Functional specification markdown
        """
        prompt = f"""
Based on the following project idea, create a comprehensive functional specification document.

PROJECT IDEA:
{project_idea}

Create a functional specification that includes:
1. Product Vision and Objectives
2. Target Users and Personas
3. Core Features and Functionality
4. User Flows and Journeys
5. Constraints and Assumptions
6. Success Criteria
7. Out of Scope (what this project will NOT include)

Format as a clear, well-structured Markdown document.
Be specific but concise. Flag any ambiguities that need clarification.
"""

        response = await self.generate_response(prompt)

        return response

    async def _generate_user_stories(
        self,
        project_idea: str,
        func_spec: str
    ) -> str:
        """
        Generate user stories.

        Args:
            project_idea: Raw project idea
            func_spec: Functional specification

        Returns:
            User stories in YAML format
        """
        prompt = f"""
Based on the functional specification, create user stories in YAML format.

FUNCTIONAL SPECIFICATION:
{func_spec[:2000]}  # Truncate for context

Create user stories following this format:

```yaml
stories:
  - id: US-001
    as_a: <user type>
    i_want: <goal>
    so_that: <benefit>
    acceptance_criteria:
      - criterion 1
      - criterion 2
      - criterion 3
    priority: high|medium|low
    estimated_effort: small|medium|large
```

Create 5-10 user stories covering the core functionality.
Each story should have clear, testable acceptance criteria.
"""

        response = await self.generate_response(prompt)

        return response
