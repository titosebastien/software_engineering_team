"""
Prompt template loader for AI agents.

This module provides utilities to load and combine prompt templates
from the prompts directory structure.
"""

from pathlib import Path
from typing import List, Optional


class PromptLoader:
    """Loads and combines prompt templates for agents."""

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the prompt loader.

        Args:
            base_path: Base path to prompts directory. Defaults to prompts/ in project root.
        """
        if base_path is None:
            # Assume we're being called from project root or a subdirectory
            project_root = Path(__file__).parent.parent
            base_path = project_root / "prompts"

        self.base = Path(base_path)

        if not self.base.exists():
            raise ValueError(f"Prompts directory not found: {self.base}")

    def load(self, *paths: str) -> str:
        """
        Load and combine multiple prompt template files.

        Args:
            *paths: Relative paths to template files (without .md extension)

        Returns:
            Combined prompt text with templates separated by newlines

        Example:
            >>> loader = PromptLoader()
            >>> prompt = loader.load("global/system", "roles/analyst")
        """
        content = []

        for path in paths:
            # Add .md extension if not present
            if not path.endswith('.md'):
                path = f"{path}.md"

            full_path = self.base / path

            if not full_path.exists():
                raise FileNotFoundError(f"Prompt template not found: {full_path}")

            template_text = full_path.read_text(encoding='utf-8')
            content.append(template_text)

        return "\n\n---\n\n".join(content)

    def load_for_role(self, role: str, include_global: bool = True) -> str:
        """
        Load prompts for a specific role.

        Args:
            role: Role name (analyst, architect, backend, frontend, designer, qa)
            include_global: Whether to include global system prompt

        Returns:
            Combined prompt for the role

        Example:
            >>> loader = PromptLoader()
            >>> analyst_prompt = loader.load_for_role("analyst")
        """
        paths = []

        if include_global:
            paths.append("global/system")

        paths.append(f"roles/{role}")

        return self.load(*paths)

    def load_for_reviewer(self, reviewer_type: str = "cto", include_global: bool = True) -> str:
        """
        Load prompts for a reviewer.

        Args:
            reviewer_type: Type of reviewer (cto, security, etc.)
            include_global: Whether to include global system prompt

        Returns:
            Combined prompt for the reviewer
        """
        paths = []

        if include_global:
            paths.append("global/system")

        paths.append(f"review/{reviewer_type}")

        return self.load(*paths)

    def list_available_roles(self) -> List[str]:
        """
        List all available role templates.

        Returns:
            List of role names (without .md extension)
        """
        roles_dir = self.base / "roles"

        if not roles_dir.exists():
            return []

        return [f.stem for f in roles_dir.glob("*.md")]

    def list_available_reviewers(self) -> List[str]:
        """
        List all available reviewer templates.

        Returns:
            List of reviewer types (without .md extension)
        """
        review_dir = self.base / "review"

        if not review_dir.exists():
            return []

        return [f.stem for f in review_dir.glob("*.md")]
