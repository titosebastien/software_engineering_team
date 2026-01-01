"""
CrewAI Implementation of AI Software Engineering Team

This is a complete reimplementation using the CrewAI framework while maintaining:
- Our prompt template organization (prompts/ folder)
- Our ADR system (memory/adr_manager.py)
- Our artifact storage (memory/artifact_store.py)

Advantages over custom implementation:
- 85% less code
- Built-in task coordination
- Mature error handling
- Active community support

Usage:
    pip install -r requirements-crewai.txt
    python main_crewai.py "Your project idea"
"""

import sys
from pathlib import Path
from typing import List, Dict

from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama

from crewai_tools import (
    create_adr_tool,
    list_adrs_tool,
    save_artifact_tool,
    read_artifact_tool,
    list_artifacts_tool,
    get_adr_manager,
    get_artifact_store
)
from config import get_settings, configure_logging


def load_prompt(role: str, include_global: bool = True) -> str:
    """
    Load prompt template from prompts folder.

    Args:
        role: Role name (analyst, architect, etc.)
        include_global: Whether to include global system rules

    Returns:
        Combined prompt text
    """
    prompts_dir = Path("prompts")

    content = []

    # Load global rules
    if include_global:
        global_prompt = prompts_dir / "global" / "system.md"
        if global_prompt.exists():
            content.append(global_prompt.read_text())
            content.append("\n---\n")

    # Load role-specific prompt
    role_prompt = prompts_dir / "roles" / f"{role}.md"
    if role_prompt.exists():
        content.append(role_prompt.read_text())
    else:
        content.append(f"You are a {role} in a software development team.")

    return "\n".join(content)


def load_cto_prompt() -> str:
    """Load CTO reviewer prompt."""
    prompts_dir = Path("prompts")

    content = []

    # Load global rules
    global_prompt = prompts_dir / "global" / "system.md"
    if global_prompt.exists():
        content.append(global_prompt.read_text())
        content.append("\n---\n")

    # Load CTO review prompt
    cto_prompt = prompts_dir / "review" / "cto.md"
    if cto_prompt.exists():
        content.append(cto_prompt.read_text())
    else:
        content.append("You are a CTO reviewing the project for production readiness.")

    return "\n".join(content)


class CrewAITeam:
    """AI Software Engineering Team using CrewAI framework."""

    def __init__(self):
        """Initialize the team with settings."""
        self.settings = get_settings()
        configure_logging(self.settings)

        print("\n" + "=" * 80)
        print("AI SOFTWARE ENGINEERING TEAM - CrewAI Implementation")
        print("=" * 80 + "\n")

    def create_llm(self, model: str) -> Ollama:
        """
        Create Ollama LLM instance.

        Args:
            model: Model name

        Returns:
            Ollama instance
        """
        return Ollama(
            model=model,
            base_url=self.settings.OLLAMA_HOST
        )

    def create_agents(self) -> Dict[str, Agent]:
        """
        Create all specialized agents using our prompt templates.

        Returns:
            Dictionary mapping role names to Agent instances
        """
        print("📋 Creating agents from prompt templates...\n")

        # LLM instances for different roles
        llm_reasoning = self.create_llm(self.settings.MODEL_ANALYST)
        llm_coding = self.create_llm(self.settings.MODEL_BACKEND)
        llm_creative = self.create_llm(self.settings.MODEL_DESIGNER)

        # Common tools for all agents
        common_tools = [
            list_adrs_tool,
            read_artifact_tool,
            list_artifacts_tool
        ]

        # Analyst Agent
        analyst = Agent(
            role='Functional Analyst',
            goal='Transform project ideas into clear functional specifications and user stories',
            backstory=load_prompt('analyst'),
            llm=llm_reasoning,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15  # Limit iterations
        )
        print("  ✓ Analyst agent created")

        # Architect Agent
        architect = Agent(
            role='Solution Architect',
            goal='Design robust, scalable system architecture with clear technical decisions',
            backstory=load_prompt('architect'),
            llm=llm_reasoning,
            tools=common_tools + [create_adr_tool, save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ Architect agent created")

        # Designer Agent
        designer = Agent(
            role='UI/UX Designer',
            goal='Create intuitive and accessible user experiences',
            backstory=load_prompt('designer'),
            llm=llm_creative,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ Designer agent created")

        # Backend Developer Agent
        backend = Agent(
            role='Backend Developer',
            goal='Plan robust backend implementation following best practices',
            backstory=load_prompt('backend'),
            llm=llm_coding,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ Backend developer agent created")

        # Frontend Developer Agent
        frontend = Agent(
            role='Frontend Developer',
            goal='Plan responsive and accessible frontend implementation',
            backstory=load_prompt('frontend'),
            llm=llm_coding,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ Frontend developer agent created")

        # QA Engineer Agent
        qa = Agent(
            role='QA Engineer',
            goal='Ensure system quality through comprehensive testing',
            backstory=load_prompt('qa'),
            llm=llm_creative,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ QA engineer agent created")

        # CTO Reviewer Agent
        cto = Agent(
            role='CTO Reviewer',
            goal='Provide executive technical review ensuring production readiness',
            backstory=load_cto_prompt(),
            llm=llm_reasoning,
            tools=common_tools + [save_artifact_tool],
            verbose=True,
            allow_delegation=False,
            max_iter=15
        )
        print("  ✓ CTO reviewer agent created")

        print(f"\n✓ Total: {7} specialized agents initialized\n")

        return {
            'analyst': analyst,
            'architect': architect,
            'designer': designer,
            'backend': backend,
            'frontend': frontend,
            'qa': qa,
            'cto': cto
        }

    def create_tasks(self, agents: Dict[str, Agent], project_idea: str) -> List[Task]:
        """
        Create sequential tasks matching our state machine workflow.

        Args:
            agents: Dictionary of agents
            project_idea: The project idea to develop

        Returns:
            List of tasks in execution order
        """
        print("📋 Creating workflow tasks...\n")

        # Task 1: Analysis
        analysis_task = Task(
            description=f"""
            Analyze the following project idea and create comprehensive deliverables:

            PROJECT IDEA:
            {project_idea}

            REQUIRED DELIVERABLES:
            1. Create functional_spec.md with:
               - Product vision and objectives
               - Target users and personas
               - Core features and functionality
               - User flows and journeys
               - Constraints and assumptions
               - Success criteria

            2. Create user_stories.yaml with:
               - User stories in proper format
               - Acceptance criteria for each story
               - Priority levels

            Use the save_artifact_tool to save both files.
            Check existing ADRs with list_adrs_tool before starting.
            """,
            agent=agents['analyst'],
            expected_output="functional_spec.md and user_stories.yaml files created",
        )
        print("  ✓ Analysis task created")

        # Task 2: Architecture
        architecture_task = Task(
            description="""
            Design the system architecture based on functional specifications.

            REQUIRED DELIVERABLES:
            1. Create architecture.md with:
               - Architecture overview and style
               - System components
               - Data model and persistence
               - Technology stack with justifications
               - Security architecture
               - Scalability considerations

            2. Create openapi.yaml with:
               - Complete API specification
               - All endpoints with request/response schemas
               - Authentication and error responses

            3. Create decisions.md with ADRs for major technical decisions

            4. Use create_adr_tool to save individual ADRs for:
               - Technology stack selection
               - Architecture pattern choice
               - Any other critical decisions

            Read functional_spec.md and user_stories.yaml using read_artifact_tool.
            Use save_artifact_tool for all deliverables.
            """,
            agent=agents['architect'],
            expected_output="architecture.md, openapi.yaml, decisions.md, and ADRs created",
            context=[analysis_task]
        )
        print("  ✓ Architecture task created")

        # Task 3: Design
        design_task = Task(
            description="""
            Create UI/UX design based on user stories and requirements.

            REQUIRED DELIVERABLES:
            1. Create design_system.md with:
               - Color palette
               - Typography scale
               - Spacing system
               - Component guidelines
               - Accessibility standards

            2. Create wireframes.md with:
               - ASCII/text-based wireframes for key screens
               - Responsive design notes
               - User flow diagrams

            Read user_stories.yaml using read_artifact_tool.
            Check ADRs with list_adrs_tool.
            Use save_artifact_tool for all deliverables.
            """,
            agent=agents['designer'],
            expected_output="design_system.md and wireframes.md created",
            context=[analysis_task]
        )
        print("  ✓ Design task created")

        # Task 4: Backend Implementation
        backend_task = Task(
            description="""
            Plan backend implementation following the architecture.

            REQUIRED DELIVERABLES:
            1. Create backend_implementation.md with:
               - Project structure
               - Main dependencies (requirements.txt excerpt)
               - Database models overview
               - API endpoints implementation notes
               - Security implementation notes
               - Testing strategy

            Read architecture.md and openapi.yaml using read_artifact_tool.
            Respect all ADRs (use list_adrs_tool).
            Use save_artifact_tool to save deliverable.
            """,
            agent=agents['backend'],
            expected_output="backend_implementation.md created",
            context=[architecture_task]
        )
        print("  ✓ Backend implementation task created")

        # Task 5: Frontend Implementation
        frontend_task = Task(
            description="""
            Plan frontend implementation following design and architecture.

            REQUIRED DELIVERABLES:
            1. Create frontend_implementation.md with:
               - Project structure (React/TypeScript)
               - Main dependencies (package.json excerpt)
               - Component hierarchy
               - State management approach
               - API integration strategy
               - Styling approach

            Read design_system.md and openapi.yaml using read_artifact_tool.
            Respect all ADRs (use list_adrs_tool).
            Use save_artifact_tool to save deliverable.
            """,
            agent=agents['frontend'],
            expected_output="frontend_implementation.md created",
            context=[architecture_task, design_task]
        )
        print("  ✓ Frontend implementation task created")

        # Task 6: Testing
        testing_task = Task(
            description="""
            Create comprehensive testing strategy and simulate results.

            REQUIRED DELIVERABLES:
            1. Create test_plan.md with:
               - Testing strategy
               - Test scenarios for all user stories
               - Edge cases and boundary conditions
               - Security testing checklist
               - Performance testing approach

            2. Create test_results.md with:
               - Simulated test execution results
               - Test coverage summary
               - Any issues found (if applicable)
               - Overall quality assessment

            Read user_stories.yaml using read_artifact_tool.
            Use save_artifact_tool for both files.
            """,
            agent=agents['qa'],
            expected_output="test_plan.md and test_results.md created",
            context=[analysis_task, backend_task, frontend_task]
        )
        print("  ✓ Testing task created")

        # Task 7: CTO Review
        review_task = Task(
            description="""
            Perform comprehensive CTO-level review of the entire project.

            REVIEW ALL ARTIFACTS:
            - Read all created artifacts using read_artifact_tool
            - Review all ADRs using list_adrs_tool

            REQUIRED DELIVERABLE:
            1. Create cto_review.md with:
               - Architecture score (X/20)
               - Security score (X/20)
               - Code quality score (X/20)
               - Scalability score (X/15)
               - Maintainability score (X/15)
               - Operational readiness score (X/10)
               - Overall score (X/100)
               - GO/NO-GO/CONDITIONAL GO decision
               - Clear rationale for decision
               - List of blockers (if NO-GO)
               - Recommendations

            Be strict and production-focused.
            Use save_artifact_tool to save the review.
            """,
            agent=agents['cto'],
            expected_output="cto_review.md with final decision",
            context=[architecture_task, backend_task, frontend_task, testing_task]
        )
        print("  ✓ CTO review task created")

        print(f"\n✓ Total: {7} tasks created (matching state machine)\n")

        return [
            analysis_task,
            architecture_task,
            design_task,
            backend_task,
            frontend_task,
            testing_task,
            review_task
        ]

    def run_project(self, project_idea: str):
        """
        Run the complete project development cycle.

        Args:
            project_idea: The project idea to develop
        """
        print("=" * 80)
        print("STARTING PROJECT DEVELOPMENT")
        print("=" * 80)
        print(f"\nProject Idea:\n{project_idea}\n")
        print("=" * 80 + "\n")

        # Create agents
        agents = self.create_agents()

        # Create tasks
        tasks = self.create_tasks(agents, project_idea)

        # Create crew
        print("📋 Assembling crew...\n")
        crew = Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process.sequential,  # Execute in order (like our state machine)
            verbose=True,
            memory=True  # Enable memory across tasks
        )
        print("✓ Crew assembled\n")

        print("=" * 80)
        print("🚀 EXECUTING PROJECT WORKFLOW")
        print("=" * 80 + "\n")

        # Execute
        try:
            result = crew.kickoff()

            print("\n" + "=" * 80)
            print("✅ PROJECT COMPLETE")
            print("=" * 80 + "\n")

            # Show final status
            self._print_final_status(result)

        except Exception as e:
            print("\n" + "=" * 80)
            print("❌ PROJECT FAILED")
            print("=" * 80)
            print(f"\nError: {e}\n")
            import traceback
            traceback.print_exc()

    def _print_final_status(self, result):
        """Print final project status."""
        print("📊 FINAL STATUS:\n")

        # Get artifact store
        artifact_store = get_artifact_store()
        artifacts = artifact_store.list_all()

        print(f"✓ Artifacts Created: {len(artifacts)}")
        for artifact in artifacts:
            print(f"  • {artifact.name} ({artifact.artifact_type.value})")

        # Get ADRs
        adr_manager = get_adr_manager()
        adrs = adr_manager.list_accepted()

        print(f"\n✓ Accepted ADRs: {len(adrs)}")
        for adr in adrs:
            print(f"  • {adr.id}: {adr.title}")

        print("\n" + "=" * 80)
        print("📁 Artifacts saved to: artifacts/")
        print("📁 ADRs saved to: artifacts/adrs/")
        print("=" * 80 + "\n")


def main():
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

    # Create and run the team
    team = CrewAITeam()

    try:
        team.run_project(project_idea)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("AI SOFTWARE ENGINEERING TEAM - CrewAI Implementation")
    print("Using prompt templates from prompts/ folder")
    print("=" * 80 + "\n")

    main()

    print("\n" + "=" * 80)
    print("Session ended")
    print("=" * 80 + "\n")
