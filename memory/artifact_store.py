"""
Artifact store for managing project deliverables.

This module provides centralized storage and retrieval of project artifacts
such as specifications, architecture documents, code, etc.
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class ArtifactType(str, Enum):
    """Types of project artifacts."""

    # Analysis phase
    FUNCTIONAL_SPEC = "functional_spec"
    USER_STORIES = "user_stories"

    # Architecture phase
    ARCHITECTURE = "architecture"
    API_SPEC = "api_spec"
    DECISIONS = "decisions"

    # Design phase
    DESIGN_SYSTEM = "design_system"
    WIREFRAMES = "wireframes"
    UX_GUIDELINES = "ux_guidelines"

    # Implementation phase
    SOURCE_CODE = "source_code"
    TESTS = "tests"
    DATABASE_SCHEMA = "database_schema"

    # Testing phase
    TEST_PLAN = "test_plan"
    TEST_RESULTS = "test_results"
    BUG_REPORT = "bug_report"

    # Review phase
    CTO_REVIEW = "cto_review"

    # Other
    DOCUMENTATION = "documentation"
    CONFIGURATION = "configuration"


class Artifact:
    """Represents a project artifact."""

    def __init__(
        self,
        name: str,
        artifact_type: ArtifactType,
        file_path: Path,
        created_by: str,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an artifact.

        Args:
            name: Artifact name
            artifact_type: Type of artifact
            file_path: Path to the artifact file
            created_by: Agent that created this artifact
            created_at: When artifact was created
            metadata: Additional metadata
        """
        self.name = name
        self.artifact_type = artifact_type
        self.file_path = file_path
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}

    def exists(self) -> bool:
        """Check if artifact file exists."""
        return self.file_path.exists()

    def read_text(self) -> str:
        """
        Read artifact content as text.

        Returns:
            Artifact content

        Raises:
            FileNotFoundError: If artifact doesn't exist
        """
        if not self.exists():
            raise FileNotFoundError(f"Artifact not found: {self.file_path}")

        return self.file_path.read_text(encoding='utf-8')

    def write_text(self, content: str) -> None:
        """
        Write text content to artifact.

        Args:
            content: Content to write
        """
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(content, encoding='utf-8')


class ArtifactStore:
    """
    Centralized store for project artifacts.

    This provides organized storage and retrieval of all project deliverables.
    """

    def __init__(self, artifacts_dir: Optional[Path] = None):
        """
        Initialize artifact store.

        Args:
            artifacts_dir: Directory for artifacts. Defaults to artifacts/
        """
        if artifacts_dir is None:
            project_root = Path(__file__).parent.parent
            artifacts_dir = project_root / "artifacts"

        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        self._ensure_structure()

        # In-memory catalog
        self._catalog: Dict[str, Artifact] = {}

        logger.info(f"Artifact store initialized at {self.artifacts_dir}")

    def _ensure_structure(self) -> None:
        """Create directory structure for different artifact types."""
        subdirs = [
            "analysis",       # Functional specs, user stories
            "architecture",   # Architecture docs, API specs, ADRs
            "design",         # Design system, wireframes
            "code",           # Source code and tests
            "testing",        # Test plans, results, bug reports
            "review",         # Review reports
            "documentation",  # General documentation
        ]

        for subdir in subdirs:
            (self.artifacts_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _get_artifact_path(self, name: str, artifact_type: ArtifactType) -> Path:
        """
        Determine the file path for an artifact based on its type.

        Args:
            name: Artifact name
            artifact_type: Type of artifact

        Returns:
            Full path where artifact should be stored
        """
        # Map artifact types to subdirectories
        type_to_dir = {
            ArtifactType.FUNCTIONAL_SPEC: "analysis",
            ArtifactType.USER_STORIES: "analysis",
            ArtifactType.ARCHITECTURE: "architecture",
            ArtifactType.API_SPEC: "architecture",
            ArtifactType.DECISIONS: "architecture",
            ArtifactType.DESIGN_SYSTEM: "design",
            ArtifactType.WIREFRAMES: "design",
            ArtifactType.UX_GUIDELINES: "design",
            ArtifactType.SOURCE_CODE: "code",
            ArtifactType.TESTS: "code",
            ArtifactType.DATABASE_SCHEMA: "code",
            ArtifactType.TEST_PLAN: "testing",
            ArtifactType.TEST_RESULTS: "testing",
            ArtifactType.BUG_REPORT: "testing",
            ArtifactType.CTO_REVIEW: "review",
            ArtifactType.DOCUMENTATION: "documentation",
            ArtifactType.CONFIGURATION: "documentation",
        }

        subdir = type_to_dir.get(artifact_type, "documentation")
        return self.artifacts_dir / subdir / name

    def store(
        self,
        name: str,
        artifact_type: ArtifactType,
        content: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Artifact:
        """
        Store an artifact.

        Args:
            name: Artifact name (e.g., "functional_spec.md")
            artifact_type: Type of artifact
            content: Artifact content
            created_by: Agent creating this artifact
            metadata: Additional metadata

        Returns:
            Created artifact
        """
        file_path = self._get_artifact_path(name, artifact_type)

        artifact = Artifact(
            name=name,
            artifact_type=artifact_type,
            file_path=file_path,
            created_by=created_by,
            metadata=metadata
        )

        # Write content
        artifact.write_text(content)

        # Add to catalog
        self._catalog[name] = artifact

        logger.info(
            f"Stored artifact '{name}' (type={artifact_type}, "
            f"created_by={created_by}) at {file_path}"
        )

        return artifact

    def retrieve(self, name: str) -> Optional[Artifact]:
        """
        Retrieve an artifact by name.

        Args:
            name: Artifact name

        Returns:
            Artifact or None if not found
        """
        # Check catalog first
        if name in self._catalog:
            return self._catalog[name]

        # Search in all subdirectories
        for subdir in self.artifacts_dir.iterdir():
            if not subdir.is_dir():
                continue

            file_path = subdir / name
            if file_path.exists():
                # Try to determine type from path
                artifact_type = self._infer_type_from_path(file_path)

                artifact = Artifact(
                    name=name,
                    artifact_type=artifact_type,
                    file_path=file_path,
                    created_by="unknown"  # Not stored in file
                )

                # Add to catalog
                self._catalog[name] = artifact

                return artifact

        logger.warning(f"Artifact not found: {name}")
        return None

    def _infer_type_from_path(self, file_path: Path) -> ArtifactType:
        """Infer artifact type from file path."""
        parent_dir = file_path.parent.name

        dir_to_type = {
            "analysis": ArtifactType.FUNCTIONAL_SPEC,
            "architecture": ArtifactType.ARCHITECTURE,
            "design": ArtifactType.DESIGN_SYSTEM,
            "code": ArtifactType.SOURCE_CODE,
            "testing": ArtifactType.TEST_PLAN,
            "review": ArtifactType.CTO_REVIEW,
        }

        return dir_to_type.get(parent_dir, ArtifactType.DOCUMENTATION)

    def list_by_type(self, artifact_type: ArtifactType) -> List[Artifact]:
        """
        List all artifacts of a specific type.

        Args:
            artifact_type: Type to filter by

        Returns:
            List of artifacts
        """
        return [
            artifact for artifact in self._catalog.values()
            if artifact.artifact_type == artifact_type
        ]

    def list_by_creator(self, created_by: str) -> List[Artifact]:
        """
        List all artifacts created by a specific agent.

        Args:
            created_by: Agent name

        Returns:
            List of artifacts
        """
        return [
            artifact for artifact in self._catalog.values()
            if artifact.created_by == created_by
        ]

    def list_all(self) -> List[Artifact]:
        """
        List all artifacts in the catalog.

        Returns:
            List of all artifacts
        """
        return list(self._catalog.values())

    def exists(self, name: str) -> bool:
        """
        Check if an artifact exists.

        Args:
            name: Artifact name

        Returns:
            True if exists
        """
        artifact = self.retrieve(name)
        return artifact is not None and artifact.exists()

    def delete(self, name: str) -> bool:
        """
        Delete an artifact.

        Args:
            name: Artifact name

        Returns:
            True if deleted, False if not found
        """
        artifact = self.retrieve(name)

        if artifact is None:
            return False

        if artifact.exists():
            artifact.file_path.unlink()

        # Remove from catalog
        self._catalog.pop(name, None)

        logger.info(f"Deleted artifact: {name}")

        return True

    def get_workspace_dir(self) -> Path:
        """
        Get the workspace directory for generated code.

        Returns:
            Path to workspace directory
        """
        workspace = self.artifacts_dir.parent / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def clear_all(self) -> None:
        """Clear all artifacts (use with caution!)."""
        for artifact in self.list_all():
            if artifact.exists():
                artifact.file_path.unlink()

        self._catalog.clear()
        logger.warning("All artifacts cleared!")
