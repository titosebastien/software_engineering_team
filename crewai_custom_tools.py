"""
Custom CrewAI tools for ADR management and artifact storage.

These tools integrate our existing memory and artifact systems with CrewAI.
"""

from crewai.tools import tool
from pathlib import Path
from typing import Optional
import yaml
from datetime import datetime

from memory.adr_manager import ADRManager, ADR, ADRType, ADRStatus
from memory.artifact_store import ArtifactStore, ArtifactType


# Initialize managers
_adr_manager = ADRManager()
_artifact_store = ArtifactStore()


@tool("Create ADR")
def create_adr_tool(
    title: str,
    decision: str,
    rationale: str,
    adr_type: str = "architecture",
    constraints: str = ""
) -> str:
    """
    Create an Architecture Decision Record (ADR).

    Use this to document important technical decisions that other agents must respect.

    Args:
        title: Short title describing the decision
        decision: What was decided
        rationale: Why this decision was made
        adr_type: Type of decision (architecture, technology, design, security, performance)
        constraints: Technical constraints imposed by this decision (comma-separated)

    Returns:
        ADR ID and confirmation message
    """
    try:
        # Parse constraints
        constraint_list = [c.strip() for c in constraints.split(",") if c.strip()]

        # Map string type to enum
        type_map = {
            "architecture": ADRType.ARCHITECTURE,
            "technology": ADRType.TECHNOLOGY,
            "design": ADRType.DESIGN,
            "security": ADRType.SECURITY,
            "performance": ADRType.PERFORMANCE,
            "data": ADRType.DATA,
            "operational": ADRType.OPERATIONAL,
        }
        adr_type_enum = type_map.get(adr_type.lower(), ADRType.ARCHITECTURE)

        # Create ADR
        adr = ADR(
            id=_adr_manager.get_next_id(),
            title=title,
            type=adr_type_enum,
            status=ADRStatus.PROPOSED,
            context=f"Decision made during automated software development",
            decision=decision,
            rationale=[rationale],
            constraints=constraint_list,
            author="crew_agent"
        )

        # Save ADR
        _adr_manager.save(adr)

        # Auto-accept (since we're in automated mode)
        _adr_manager.accept_adr(adr.id)

        return f"✓ Created and accepted {adr.id}: {title}"

    except Exception as e:
        return f"✗ Error creating ADR: {str(e)}"


@tool("List ADRs")
def list_adrs_tool() -> str:
    """
    List all accepted Architecture Decision Records.

    Use this to see what architectural constraints and decisions are currently active.
    You MUST respect all accepted ADRs in your work.

    Returns:
        Summary of all accepted ADRs
    """
    try:
        adrs = _adr_manager.list_accepted()

        if not adrs:
            return "No ADRs yet."

        summary = ["ACCEPTED ARCHITECTURE DECISION RECORDS:\n"]
        for adr in adrs:
            summary.append(f"\n{adr.id}: {adr.title}")
            summary.append(f"  Decision: {adr.decision}")
            if adr.constraints:
                summary.append(f"  Constraints: {', '.join(adr.constraints)}")

        return "\n".join(summary)

    except Exception as e:
        return f"Error listing ADRs: {str(e)}"


@tool("Save Artifact")
def save_artifact_tool(
    filename: str,
    content: str,
    artifact_type: str = "documentation",
    description: str = ""
) -> str:
    """
    Save a project artifact (document, specification, code, etc.).

    Use this to store all deliverables so they can be accessed by other agents.

    Args:
        filename: Name of the file (e.g., "functional_spec.md")
        content: Full content of the artifact
        artifact_type: Type (functional_spec, user_stories, architecture, api_spec,
                       design_system, source_code, test_plan, test_results, cto_review)
        description: Brief description of this artifact

    Returns:
        Confirmation message with file location
    """
    try:
        # Map string type to enum
        type_map = {
            "functional_spec": ArtifactType.FUNCTIONAL_SPEC,
            "user_stories": ArtifactType.USER_STORIES,
            "architecture": ArtifactType.ARCHITECTURE,
            "api_spec": ArtifactType.API_SPEC,
            "decisions": ArtifactType.DECISIONS,
            "design_system": ArtifactType.DESIGN_SYSTEM,
            "wireframes": ArtifactType.WIREFRAMES,
            "ux_guidelines": ArtifactType.UX_GUIDELINES,
            "source_code": ArtifactType.SOURCE_CODE,
            "tests": ArtifactType.TESTS,
            "test_plan": ArtifactType.TEST_PLAN,
            "test_results": ArtifactType.TEST_RESULTS,
            "bug_report": ArtifactType.BUG_REPORT,
            "cto_review": ArtifactType.CTO_REVIEW,
            "documentation": ArtifactType.DOCUMENTATION,
        }
        artifact_type_enum = type_map.get(artifact_type.lower(), ArtifactType.DOCUMENTATION)

        # Store artifact
        artifact = _artifact_store.store(
            name=filename,
            artifact_type=artifact_type_enum,
            content=content,
            created_by="crew_agent",
            metadata={"description": description}
        )

        return f"✓ Saved {filename} to {artifact.file_path}"

    except Exception as e:
        return f"✗ Error saving artifact: {str(e)}"


@tool("Read Artifact")
def read_artifact_tool(filename: str) -> str:
    """
    Read a previously saved artifact.

    Use this to access deliverables from previous phases or other agents.

    Args:
        filename: Name of the file to read

    Returns:
        Content of the artifact or error message
    """
    try:
        artifact = _artifact_store.retrieve(filename)

        if not artifact:
            # List available artifacts
            available = _artifact_store.list_all()
            filenames = [a.name for a in available]
            return f"Artifact '{filename}' not found. Available: {', '.join(filenames)}"

        content = artifact.read_text()
        return f"Content of {filename}:\n\n{content}"

    except Exception as e:
        return f"Error reading artifact: {str(e)}"


@tool("List Artifacts")
def list_artifacts_tool() -> str:
    """
    List all available artifacts.

    Use this to see what deliverables have been created so far.

    Returns:
        List of all artifacts with their types
    """
    try:
        artifacts = _artifact_store.list_all()

        if not artifacts:
            return "No artifacts yet."

        summary = ["AVAILABLE ARTIFACTS:\n"]
        for artifact in artifacts:
            summary.append(f"  • {artifact.name} ({artifact.artifact_type.value})")

        return "\n".join(summary)

    except Exception as e:
        return f"Error listing artifacts: {str(e)}"


# Export managers for direct access if needed
def get_adr_manager() -> ADRManager:
    """Get the global ADR manager instance."""
    return _adr_manager


def get_artifact_store() -> ArtifactStore:
    """Get the global artifact store instance."""
    return _artifact_store
