"""
CrewAI Implementation Prototype

This demonstrates what the same system would look like using CrewAI framework.
Compare with main.py to see the difference.

Installation:
    pip install crewai crewai-tools langchain-community

Usage:
    python crewai_prototype.py "Your project idea"
"""

from crewai import Agent, Task, Crew, Process
from langchain_community.llms import Ollama
from pathlib import Path
import sys


def load_prompt(role: str) -> str:
    """Load prompt template from file."""
    prompt_path = Path("prompts/roles") / f"{role}.md"
    if prompt_path.exists():
        return prompt_path.read_text()
    return f"You are a {role} agent in a software development team."


def create_agents():
    """Create all specialized agents."""

    # LLM instances
    llm_reasoning = Ollama(model="qwen2.5:14b")
    llm_coding = Ollama(model="deepseek-coder:6.7b")
    llm_creative = Ollama(model="mistral:7b")

    # Analyst Agent
    analyst = Agent(
        role='Functional Analyst',
        goal='Transform project ideas into clear functional specifications and user stories',
        backstory=load_prompt('analyst'),
        llm=llm_reasoning,
        verbose=True,
        allow_delegation=False
    )

    # Architect Agent
    architect = Agent(
        role='Solution Architect',
        goal='Design robust, scalable system architecture with clear technical decisions',
        backstory=load_prompt('architect'),
        llm=llm_reasoning,
        verbose=True,
        allow_delegation=False
    )

    # Designer Agent
    designer = Agent(
        role='UI/UX Designer',
        goal='Create intuitive and accessible user experiences',
        backstory=load_prompt('designer'),
        llm=llm_creative,
        verbose=True,
        allow_delegation=False
    )

    # Backend Developer Agent
    backend = Agent(
        role='Backend Developer',
        goal='Implement robust backend services following best practices',
        backstory=load_prompt('backend'),
        llm=llm_coding,
        verbose=True,
        allow_delegation=False
    )

    # Frontend Developer Agent
    frontend = Agent(
        role='Frontend Developer',
        goal='Build responsive and accessible user interfaces',
        backstory=load_prompt('frontend'),
        llm=llm_coding,
        verbose=True,
        allow_delegation=False
    )

    # QA Engineer Agent
    qa = Agent(
        role='QA Engineer',
        goal='Ensure system quality through comprehensive testing',
        backstory=load_prompt('qa'),
        llm=llm_creative,
        verbose=True,
        allow_delegation=False
    )

    # CTO Reviewer Agent
    cto = Agent(
        role='CTO Reviewer',
        goal='Provide executive technical review ensuring production readiness',
        backstory=load_prompt('cto'),
        llm=llm_reasoning,
        verbose=True,
        allow_delegation=False
    )

    return {
        'analyst': analyst,
        'architect': architect,
        'designer': designer,
        'backend': backend,
        'frontend': frontend,
        'qa': qa,
        'cto': cto
    }


def create_tasks(agents, project_idea):
    """Create sequential tasks for the workflow."""

    # Analysis Task
    analysis_task = Task(
        description=f"""
        Analyze the following project idea and create:
        1. A comprehensive functional specification
        2. User stories with acceptance criteria

        Project Idea: {project_idea}

        Produce well-structured documents that capture all requirements clearly.
        """,
        agent=agents['analyst'],
        expected_output="Functional specification and user stories documents"
    )

    # Architecture Task
    architecture_task = Task(
        description="""
        Based on the functional specification, design:
        1. System architecture
        2. API specifications (OpenAPI format)
        3. Architecture Decision Records (ADRs) for key technical choices

        Ensure the architecture is scalable, secure, and maintainable.
        """,
        agent=agents['architect'],
        expected_output="Architecture document, API spec, and ADRs",
        context=[analysis_task]  # Depends on analysis
    )

    # Design Task
    design_task = Task(
        description="""
        Create UI/UX design including:
        1. Design system (colors, typography, components)
        2. Wireframes for key screens
        3. UX guidelines

        Ensure accessibility and user-centered design.
        """,
        agent=agents['designer'],
        expected_output="Design system and wireframes",
        context=[analysis_task]
    )

    # Backend Implementation Task
    backend_task = Task(
        description="""
        Plan backend implementation:
        1. Project structure
        2. Database models
        3. API endpoints
        4. Key implementation notes

        Follow the architecture and API specifications strictly.
        """,
        agent=agents['backend'],
        expected_output="Backend implementation plan",
        context=[architecture_task]
    )

    # Frontend Implementation Task
    frontend_task = Task(
        description="""
        Plan frontend implementation:
        1. Component structure
        2. State management approach
        3. API integration strategy
        4. Key implementation notes

        Follow the design system and API specifications.
        """,
        agent=agents['frontend'],
        expected_output="Frontend implementation plan",
        context=[architecture_task, design_task]
    )

    # Testing Task
    testing_task = Task(
        description="""
        Create comprehensive testing strategy:
        1. Test plan covering all user stories
        2. Test scenarios and edge cases
        3. Quality criteria
        4. Simulated test results

        Be thorough and adversarial in testing approach.
        """,
        agent=agents['qa'],
        expected_output="Test plan and results",
        context=[analysis_task, backend_task, frontend_task]
    )

    # CTO Review Task
    review_task = Task(
        description="""
        Perform executive technical review covering:
        1. Architecture quality and scalability
        2. Security assessment
        3. Code quality (based on plans)
        4. Operational readiness
        5. Overall GO/NO-GO decision with score

        Be strict and production-focused.
        """,
        agent=agents['cto'],
        expected_output="CTO review report with decision",
        context=[architecture_task, backend_task, frontend_task, testing_task]
    )

    return [
        analysis_task,
        architecture_task,
        design_task,
        backend_task,
        frontend_task,
        testing_task,
        review_task
    ]


def main():
    """Main entry point."""

    # Get project idea
    if len(sys.argv) > 1:
        project_idea = " ".join(sys.argv[1:])
    else:
        project_idea = """
        Create a simple Todo API application that allows users to:
        - Create, read, update, and delete todo items
        - Mark todos as completed
        - Filter todos by status (completed/pending)

        The API should be RESTful with proper HTTP methods and status codes.
        """

    print("=" * 80)
    print("AI SOFTWARE ENGINEERING TEAM - CrewAI Implementation")
    print("=" * 80)
    print(f"\nProject Idea: {project_idea}\n")
    print("=" * 80)

    # Create agents
    print("\n📋 Creating agents...")
    agents = create_agents()
    print(f"✓ Created {len(agents)} specialized agents\n")

    # Create tasks
    print("📋 Creating workflow tasks...")
    tasks = create_tasks(agents, project_idea)
    print(f"✓ Created {len(tasks)} sequential tasks\n")

    # Create crew
    print("📋 Assembling crew...")
    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,  # Execute tasks in order
        verbose=True,
        memory=True  # Enable memory across tasks
    )
    print("✓ Crew assembled\n")

    print("=" * 80)
    print("🚀 STARTING PROJECT EXECUTION")
    print("=" * 80 + "\n")

    # Execute
    try:
        result = crew.kickoff()

        print("\n" + "=" * 80)
        print("✅ PROJECT COMPLETE")
        print("=" * 80)
        print("\n📊 Final Output:")
        print(result)
        print("\n" + "=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ PROJECT FAILED")
        print("=" * 80)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    COMPARISON WITH CUSTOM IMPLEMENTATION:

    Custom Implementation (main.py):
        - ~4,270 lines of infrastructure code
        - Custom event bus, state machine, orchestrator
        - Manual message passing
        - Complex error handling
        - Requires deep understanding of system

    CrewAI Implementation (this file):
        - ~280 lines total
        - Built-in coordination and memory
        - Automatic task delegation
        - Framework handles complexity
        - Focus on business logic only

    Code Reduction: ~94% less code
    Complexity Reduction: Significant
    Feature Parity: Similar (some differences)

    Trade-offs:
        + Much simpler and faster to develop
        + Battle-tested framework
        + Rich ecosystem and tools
        + Active community support
        - Less control over internals
        - Framework dependency
        - Some "magic" behavior
        - May not match exact SOC.txt vision
    """
    main()
