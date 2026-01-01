"""
CTO Reviewer agent.

This agent provides executive-level technical review before delivery.
"""

import logging
from typing import Dict, Any

from agents.base import BaseAgent
from memory.artifact_store import ArtifactType
from llm.prompt_loader import PromptLoader


logger = logging.getLogger(__name__)


class CTOReviewerAgent(BaseAgent):
    """
    CTO Reviewer agent.

    Provides final technical review covering architecture, security,
    code quality, and operational readiness.
    """

    def __init__(self, *args, **kwargs):
        """Initialize CTO reviewer with special prompt."""
        # Don't call super().__init__ yet - we need to override the prompt loading
        self._pre_init_done = False
        super().__init__(*args, **kwargs)

    def _load_system_prompt(self) -> str:
        """Load CTO reviewer prompt."""
        loader = PromptLoader()
        return loader.load_for_reviewer("cto", include_global=True)

    async def execute_task(self, task: Dict[str, Any]) -> None:
        """
        Execute CTO review task.

        Args:
            task: Task data
        """
        logger.info(f"{self.name} starting CTO review")

        try:
            # Gather all artifacts for review
            await self.send_status("Gathering all project artifacts...")

            artifacts = self._gather_all_artifacts()

            # Perform comprehensive review
            await self.send_status("Performing comprehensive technical review...")

            review = await self._perform_review(artifacts)

            # Parse decision from review
            decision, score = self._parse_review_decision(review)

            # Store review
            self.artifact_store.store(
                name="cto_review.md",
                artifact_type=ArtifactType.CTO_REVIEW,
                content=review,
                created_by=self.name
            )

            # Submit deliverable with decision
            await self.submit_deliverable(
                summary=f"CTO Review complete: {decision}",
                artifacts=["cto_review.md"],
                additional_data={
                    "decision": decision,
                    "score": score,
                    "phase": "review"
                }
            )

            logger.info(f"{self.name} completed review: {decision} (score={score})")

        except Exception as e:
            logger.error(f"{self.name} error during review: {e}", exc_info=True)
            await self._send_error(str(e), "review_error")

    def _gather_all_artifacts(self) -> Dict[str, str]:
        """
        Gather all project artifacts for review.

        Returns:
            Dictionary mapping artifact names to content
        """
        artifacts = {}

        artifact_names = [
            "functional_spec.md",
            "user_stories.yaml",
            "architecture.md",
            "openapi.yaml",
            "decisions.md",
            "design_system.md",
            "test_plan.md",
            "test_results.md"
        ]

        for name in artifact_names:
            artifact = self.artifact_store.retrieve(name)
            if artifact and artifact.exists():
                try:
                    artifacts[name] = artifact.read_text()
                except Exception as e:
                    logger.warning(f"Could not read artifact {name}: {e}")
                    artifacts[name] = "[ERROR READING FILE]"
            else:
                artifacts[name] = "[NOT FOUND]"

        # Also include ADRs
        adrs = self.adr_manager.list_accepted()
        adr_summary = "\n\n".join([
            f"## {adr.id}: {adr.title}\n{adr.decision}"
            for adr in adrs
        ])
        artifacts["adrs"] = adr_summary

        return artifacts

    async def _perform_review(self, artifacts: Dict[str, str]) -> str:
        """
        Perform comprehensive CTO review.

        Args:
            artifacts: All project artifacts

        Returns:
            Review document
        """
        # Build comprehensive context
        context = "# PROJECT ARTIFACTS FOR REVIEW\n\n"

        for name, content in artifacts.items():
            # Truncate large artifacts
            truncated = content[:2000] if len(content) > 2000 else content
            context += f"\n## {name}\n\n```\n{truncated}\n```\n\n"

        prompt = f"""
You are conducting a CTO-level review of this software project.

{context}

Provide a comprehensive review covering:

1. **Architecture** (Score: X/20)
   - Strengths
   - Weaknesses
   - Recommendations

2. **Security** (Score: X/20)
   - Strengths
   - Critical Issues (if any)
   - Recommendations

3. **Code Quality** (Score: X/20)
   - Assessment based on architecture and design
   - Concerns

4. **Scalability** (Score: X/15)
   - Current capacity estimate
   - Bottlenecks
   - Recommendations

5. **Maintainability** (Score: X/15)
   - Assessment
   - Concerns

6. **Operational Readiness** (Score: X/10)
   - Deployment considerations
   - Monitoring and logging

**Overall Score**: X/100

**DECISION**: GO | NO-GO | CONDITIONAL GO

**Rationale**: [Clear explanation of decision]

**Blockers** (if NO-GO):
- Blocker 1
- Blocker 2

Be strict but fair. Score honestly based on production standards.
"""

        review = await self.generate_response(prompt, temperature=0.1)

        return review

    def _parse_review_decision(self, review: str) -> tuple[str, int]:
        """
        Parse decision and score from review.

        Args:
            review: Review document

        Returns:
            Tuple of (decision, score)
        """
        decision = "CONDITIONAL GO"  # Default
        score = 75  # Default

        review_upper = review.upper()

        # Extract decision
        if "DECISION: GO" in review_upper and "NO-GO" not in review_upper.split("DECISION: GO")[0]:
            decision = "GO"
        elif "DECISION: NO-GO" in review_upper or "DECISION: NOGO" in review_upper:
            decision = "NO-GO"
        elif "CONDITIONAL GO" in review_upper:
            decision = "CONDITIONAL GO"

        # Extract score
        import re
        score_match = re.search(r'OVERALL SCORE.*?(\d+)/100', review, re.IGNORECASE)
        if score_match:
            score = int(score_match.group(1))

        logger.info(f"Parsed review: decision={decision}, score={score}")

        return decision, score
