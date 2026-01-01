"""
Architecture Decision Records (ADR) Manager.

This module manages ADRs which are the immutable memory of architectural
and technical decisions made during the project. ADRs prevent context loss
and ensure agents respect previous decisions.
"""

import yaml
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ADRStatus(str, Enum):
    """Status of an Architecture Decision Record."""

    PROPOSED = "proposed"      # Decision has been proposed but not accepted
    ACCEPTED = "accepted"      # Decision is active and must be respected
    DEPRECATED = "deprecated"  # Decision has been superseded
    REJECTED = "rejected"      # Decision was considered but rejected


class ADRType(str, Enum):
    """Type of architectural decision."""

    ARCHITECTURE = "architecture"  # System architecture decisions
    TECHNOLOGY = "technology"      # Technology stack choices
    DESIGN = "design"              # Design patterns and principles
    SECURITY = "security"          # Security-related decisions
    PERFORMANCE = "performance"    # Performance and optimization
    OPERATIONAL = "operational"    # Operations and deployment
    DATA = "data"                  # Data models and persistence


class ADR(BaseModel):
    """
    Architecture Decision Record.

    ADRs document important technical decisions to prevent context loss
    and ensure consistency across the project lifecycle.
    """

    id: str = Field(..., description="Unique ADR identifier (e.g., ADR-001)")
    title: str = Field(..., description="Short title describing the decision")
    status: ADRStatus = Field(default=ADRStatus.PROPOSED, description="Current status")
    type: ADRType = Field(..., description="Type of decision")
    date: datetime = Field(default_factory=datetime.utcnow, description="When decision was made")

    # Decision content
    context: str = Field(..., description="Why this decision is needed")
    decision: str = Field(..., description="What we decided to do")
    rationale: List[str] = Field(default_factory=list, description="Reasons for this decision")

    # Impact analysis
    consequences: Dict[str, List[str]] = Field(
        default_factory=lambda: {"positive": [], "negative": [], "tradeoffs": []},
        description="Consequences of this decision"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Technical constraints imposed by this decision"
    )
    affected_components: List[str] = Field(
        default_factory=list,
        description="Which components are affected"
    )

    # Metadata
    author: str = Field(..., description="Who made this decision (usually agent name)")
    supersedes: Optional[str] = Field(
        default=None,
        description="ADR ID that this decision supersedes (if any)"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_yaml(self) -> str:
        """
        Convert ADR to YAML format for storage.

        Returns:
            YAML string representation
        """
        data = self.dict()
        # Convert enums to strings for YAML
        data['status'] = data['status'].value if isinstance(data['status'], Enum) else data['status']
        data['type'] = data['type'].value if isinstance(data['type'], Enum) else data['type']
        # Convert datetime to ISO string
        if isinstance(data['date'], datetime):
            data['date'] = data['date'].isoformat()

        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'ADR':
        """
        Create ADR from YAML string.

        Args:
            yaml_str: YAML representation

        Returns:
            ADR instance
        """
        data = yaml.safe_load(yaml_str)
        return cls(**data)


class ADRManager:
    """
    Manager for Architecture Decision Records.

    This class provides CRUD operations for ADRs and ensures
    they are properly stored and accessible to all agents.
    """

    def __init__(self, adr_dir: Optional[Path] = None):
        """
        Initialize ADR manager.

        Args:
            adr_dir: Directory to store ADRs. Defaults to artifacts/adrs/
        """
        if adr_dir is None:
            # Default to artifacts/adrs/ relative to project root
            project_root = Path(__file__).parent.parent
            adr_dir = project_root / "artifacts" / "adrs"

        self.adr_dir = Path(adr_dir)
        self.adr_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ADR Manager initialized with directory: {self.adr_dir}")

    def save(self, adr: ADR) -> Path:
        """
        Save an ADR to disk.

        Args:
            adr: ADR to save

        Returns:
            Path where ADR was saved
        """
        file_path = self.adr_dir / f"{adr.id}.yaml"

        with open(file_path, 'w') as f:
            f.write(adr.to_yaml())

        logger.info(f"Saved ADR {adr.id}: {adr.title} (status={adr.status})")

        return file_path

    def load(self, adr_id: str) -> Optional[ADR]:
        """
        Load an ADR by ID.

        Args:
            adr_id: ADR identifier

        Returns:
            ADR instance or None if not found
        """
        file_path = self.adr_dir / f"{adr_id}.yaml"

        if not file_path.exists():
            logger.warning(f"ADR not found: {adr_id}")
            return None

        with open(file_path, 'r') as f:
            yaml_str = f.read()

        adr = ADR.from_yaml(yaml_str)
        logger.debug(f"Loaded ADR {adr_id}")

        return adr

    def list_all(self) -> List[ADR]:
        """
        List all ADRs.

        Returns:
            List of all ADRs sorted by date
        """
        adrs = []

        for file_path in self.adr_dir.glob("*.yaml"):
            try:
                with open(file_path, 'r') as f:
                    adr = ADR.from_yaml(f.read())
                    adrs.append(adr)
            except Exception as e:
                logger.error(f"Failed to load ADR from {file_path}: {e}")

        # Sort by date
        adrs.sort(key=lambda x: x.date)

        return adrs

    def list_by_status(self, status: ADRStatus) -> List[ADR]:
        """
        List ADRs filtered by status.

        Args:
            status: ADR status to filter by

        Returns:
            List of ADRs with the specified status
        """
        all_adrs = self.list_all()
        filtered = [adr for adr in all_adrs if adr.status == status]

        logger.debug(f"Found {len(filtered)} ADRs with status={status}")

        return filtered

    def list_accepted(self) -> List[ADR]:
        """
        List all ACCEPTED ADRs.

        These are the active decisions that agents MUST respect.

        Returns:
            List of accepted ADRs
        """
        return self.list_by_status(ADRStatus.ACCEPTED)

    def list_by_type(self, adr_type: ADRType) -> List[ADR]:
        """
        List ADRs filtered by type.

        Args:
            adr_type: Type to filter by

        Returns:
            List of ADRs of the specified type
        """
        all_adrs = self.list_all()
        filtered = [adr for adr in all_adrs if adr.type == adr_type]

        return filtered

    def update_status(self, adr_id: str, new_status: ADRStatus) -> bool:
        """
        Update the status of an ADR.

        Args:
            adr_id: ADR identifier
            new_status: New status

        Returns:
            True if updated, False if ADR not found
        """
        adr = self.load(adr_id)

        if adr is None:
            return False

        old_status = adr.status
        adr.status = new_status

        self.save(adr)

        logger.info(
            f"Updated ADR {adr_id} status: {old_status} -> {new_status}"
        )

        return True

    def accept_adr(self, adr_id: str) -> bool:
        """
        Accept a proposed ADR, making it active.

        Args:
            adr_id: ADR to accept

        Returns:
            True if successful
        """
        return self.update_status(adr_id, ADRStatus.ACCEPTED)

    def deprecate_adr(self, adr_id: str, superseded_by: Optional[str] = None) -> bool:
        """
        Deprecate an ADR.

        Args:
            adr_id: ADR to deprecate
            superseded_by: ID of ADR that supersedes this one

        Returns:
            True if successful
        """
        success = self.update_status(adr_id, ADRStatus.DEPRECATED)

        if success and superseded_by:
            # Update the new ADR to reference this one
            new_adr = self.load(superseded_by)
            if new_adr:
                new_adr.supersedes = adr_id
                self.save(new_adr)

        return success

    def get_next_id(self) -> str:
        """
        Get the next available ADR ID.

        Returns:
            Next ADR ID (e.g., "ADR-005")
        """
        all_adrs = self.list_all()

        if not all_adrs:
            return "ADR-001"

        # Extract numbers from IDs
        numbers = []
        for adr in all_adrs:
            try:
                num = int(adr.id.split('-')[1])
                numbers.append(num)
            except (IndexError, ValueError):
                continue

        if numbers:
            next_num = max(numbers) + 1
        else:
            next_num = 1

        return f"ADR-{next_num:03d}"

    def search(self, query: str) -> List[ADR]:
        """
        Search ADRs by text in title, context, or decision.

        Args:
            query: Search query

        Returns:
            List of matching ADRs
        """
        all_adrs = self.list_all()
        query_lower = query.lower()

        results = []
        for adr in all_adrs:
            if (query_lower in adr.title.lower() or
                query_lower in adr.context.lower() or
                query_lower in adr.decision.lower()):
                results.append(adr)

        logger.debug(f"Search for '{query}' found {len(results)} ADRs")

        return results

    def get_constraints_summary(self) -> Dict[str, List[str]]:
        """
        Get a summary of all constraints from accepted ADRs.

        This is useful for agents to quickly see what constraints they must respect.

        Returns:
            Dictionary mapping ADR IDs to their constraints
        """
        accepted = self.list_accepted()
        summary = {}

        for adr in accepted:
            if adr.constraints:
                summary[adr.id] = adr.constraints

        return summary
