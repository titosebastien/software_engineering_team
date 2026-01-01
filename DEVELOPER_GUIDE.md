# Developer Guide - AI Software Engineering Team

**For AI Agent Continuity**

This document provides comprehensive guidance for any AI agent (including Claude) that needs to continue development, debug, or extend this system. It captures the principles, patterns, architecture decisions, and conventions followed during implementation.

---

## Table of Contents

1. [Project Context](#project-context)
2. [Core Principles](#core-principles)
3. [Architecture Overview](#architecture-overview)
4. [Design Patterns](#design-patterns)
5. [Implementation Guidelines](#implementation-guidelines)
6. [Code Organization](#code-organization)
7. [Extension Points](#extension-points)
8. [Common Tasks](#common-tasks)
9. [Debugging Guide](#debugging-guide)
10. [What's Complete vs. What's Not](#whats-complete-vs-whats-not)
11. [Known Limitations](#known-limitations)
12. [Future Improvements](#future-improvements)

---

## Project Context

### Origin
This system was built based on a conversation transcript (SOC.txt) about creating an autonomous AI software engineering team. The conversation outlined a multi-agent system where specialized AI agents collaborate to develop software from idea to delivery.

### Primary Goal
Create a production-grade, autonomous multi-agent system that can:
- Accept a project idea
- Analyze requirements
- Design architecture
- Plan implementation
- Test the system
- Deliver a reviewed, production-ready design

### Key Constraints
1. **No external API costs**: Use only open-source, local LLMs (Ollama)
2. **No hallucination**: Enforce architectural constraints via ADRs
3. **No context loss**: Use persistent memory (ADRs) to preserve decisions
4. **Structured communication**: No free-form agent chatter, only structured messages
5. **GitOps**: Each feature branch → test → merge workflow

---

## Core Principles

### 1. Separation of Concerns

**Principle**: Each component has a single, well-defined responsibility.

**Applied**:
- Agents: Domain expertise only (analyst doesn't design, architect doesn't code)
- Orchestrator: Workflow management only (doesn't produce deliverables)
- Event Bus: Communication only (doesn't process business logic)
- Memory Manager: Persistence only (doesn't make decisions)

**Why**: Reduces coupling, improves testability, makes system easier to understand and extend.

### 2. Prompt Templates Are Configuration, Not Code

**Principle**: Prompts are externalized in `prompts/` directory, not hardcoded in Python.

**Applied**:
- All agent prompts in `prompts/roles/*.md`
- Global rules in `prompts/global/system.md`
- Review prompts in `prompts/review/*.md`
- Loaded dynamically via `PromptLoader`

**Why**:
- Version control for prompts
- Easy A/B testing
- Non-developers can modify agent behavior
- Prompts are the "programming language" for LLMs - they should be first-class citizens

### 3. Type Safety and Validation

**Principle**: Use Pydantic for all data structures and configurations.

**Applied**:
- Message schemas (`communication/schemas.py`)
- Configuration (`config.py`)
- ADR structure (`memory/adr_manager.py`)
- Enum types for states, message types, ADR statuses

**Why**: Catch errors early, provide IDE autocomplete, document data structures, enable runtime validation.

### 4. Async-First Architecture

**Principle**: All I/O operations are async, enabling concurrent agent operations.

**Applied**:
- All agent methods are `async def`
- Event bus uses `asyncio.Queue`
- LLM calls are async
- Orchestrator runs agents concurrently

**Why**: Agents can work in parallel, system is more responsive, better resource utilization.

### 5. Immutable Architectural Decisions

**Principle**: Once an ADR is ACCEPTED, it becomes an immutable constraint that agents MUST respect.

**Applied**:
- ADRs have status: PROPOSED → ACCEPTED → DEPRECATED
- Only CTO or human can deprecate an ADR
- Every agent loads ACCEPTED ADRs before acting
- ADRs are injected into LLM context automatically

**Why**: Prevents agents from contradicting previous decisions, solves the "context loss" problem at scale.

### 6. Evidence-Based Progression

**Principle**: No state transition without deliverables.

**Applied**:
- Each state has required deliverables (defined in `StateMachine`)
- Orchestrator validates deliverables before transitioning
- Deliverables are stored in artifact store
- Failed validation blocks progression

**Why**: Ensures quality gates, prevents skipping work, provides audit trail.

### 7. Structured Communication Only

**Principle**: Agents communicate via typed messages, never free-form strings.

**Applied**:
- `Message` base class with subtypes (TaskMessage, DeliverableMessage, etc.)
- JSON-serializable message schemas
- Event bus enforces message structure
- No direct agent-to-agent calls (everything via bus)

**Why**: Debuggable, traceable, type-safe, enables message persistence/replay.

---

## Architecture Overview

### Layer Model

```
┌─────────────────────────────────────────┐
│  Entry Point (main.py)                  │
├─────────────────────────────────────────┤
│  Configuration (config.py)              │
├─────────────────────────────────────────┤
│  Orchestration Layer                    │
│  ├─ Orchestrator (workflow manager)     │
│  └─ StateMachine (state transitions)    │
├─────────────────────────────────────────┤
│  Agent Layer                             │
│  ├─ BaseAgent (common functionality)    │
│  └─ Specialized Agents (domain logic)   │
├─────────────────────────────────────────┤
│  Infrastructure Layer                   │
│  ├─ Event Bus (communication)           │
│  ├─ Memory Manager (ADRs, artifacts)    │
│  └─ LLM Factory (model access)          │
├─────────────────────────────────────────┤
│  External Dependencies                  │
│  └─ Ollama (LLM inference)              │
└─────────────────────────────────────────┘
```

### Data Flow

1. **Idea Input** → Orchestrator
2. **Orchestrator** → Assigns task → Agent via Event Bus
3. **Agent** → Loads ADRs from Memory Manager
4. **Agent** → Generates response via LLM
5. **Agent** → Stores artifacts in Artifact Store
6. **Agent** → Submits deliverable → Orchestrator via Event Bus
7. **Orchestrator** → Validates deliverables
8. **Orchestrator** → Transitions state
9. **Orchestrator** → Assigns next task
10. Repeat until DELIVERY or FAILED

### State Machine

The system progresses through states in strict order:

```
IDEA
  ↓
ANALYSIS (Analyst)
  ↓
ARCHITECTURE (Architect)
  ↓
DESIGN (Designer)
  ↓
IMPLEMENTATION (Backend + Frontend)
  ↓
TESTING (QA)
  ↓
REVIEW (CTO)
  ↓
DELIVERY
```

**Key invariant**: Cannot skip states. Must produce required deliverables to advance.

---

## Design Patterns

### 1. Template Method Pattern

**Where**: `BaseAgent` class

**How**:
- `execute_task()` is abstract (template method)
- Common functionality (LLM interaction, ADR loading, message sending) in base class
- Specialization via override

**Example**:
```python
class AnalystAgent(BaseAgent):
    async def execute_task(self, task):
        # Analyst-specific logic
        spec = await self.generate_response(...)
        self.artifact_store.store(...)
        await self.submit_deliverable(...)
```

### 2. Factory Pattern

**Where**: `LLMFactory` (`llm/factory.py`)

**How**:
- Creates role-appropriate LLM instances
- Encapsulates model selection logic
- Configurable via settings

**Example**:
```python
llm = create_llm_for_role("analyst")  # Gets qwen2.5:14b
llm = create_llm_for_role("backend")  # Gets deepseek-coder:6.7b
```

### 3. Observer Pattern

**Where**: Event Bus broadcasting

**How**:
- Agents subscribe to event bus
- State changes broadcast to all subscribers
- Decoupled notification system

### 4. State Pattern

**Where**: `StateMachine`

**How**:
- Project state determines valid transitions
- Each state has associated agent and deliverables
- State-specific behavior encapsulated

### 5. Repository Pattern

**Where**: `ADRManager`, `ArtifactStore`

**How**:
- Abstract storage operations
- Hide persistence details
- Provide clean query interface

---

## Implementation Guidelines

### Adding a New Agent

**Steps**:

1. **Create prompt template** in `prompts/roles/new_agent.md`:
   ```markdown
   # Role: New Agent Name

   ## MISSION:
   What this agent does

   ## RESPONSIBILITIES:
   - Responsibility 1
   - Responsibility 2

   ## INPUT:
   What this agent receives

   ## OUTPUT:
   What this agent produces

   ## RULES:
   Constraints and guidelines
   ```

2. **Create agent class** in `agents/new_agent.py`:
   ```python
   from agents.base import BaseAgent

   class NewAgent(BaseAgent):
       async def execute_task(self, task: Dict[str, Any]) -> None:
           # 1. Load context
           # 2. Generate output via LLM
           # 3. Store artifacts
           # 4. Submit deliverable
   ```

3. **Register in state machine** (`core/state_machine.py`):
   ```python
   STATE_AGENT_MAP = {
       ProjectState.NEW_STATE: "new_agent",
       # ...
   }
   ```

4. **Initialize in main.py**:
   ```python
   agent = NewAgent(
       name="new_agent",
       role="new_agent",
       event_bus=self.event_bus,
       adr_manager=self.adr_manager,
       artifact_store=self.artifact_store
   )
   self.agents["new_agent"] = agent
   ```

5. **Add model mapping** in `config.py` or `llm/factory.py`:
   ```python
   MODEL_NEW_AGENT: str = Field(default="qwen2.5:14b")
   ```

### Adding a New Project State

**Steps**:

1. **Add to enum** in `core/state_machine.py`:
   ```python
   class ProjectState(str, Enum):
       NEW_STATE = "new_state"
   ```

2. **Define transitions**:
   ```python
   TRANSITIONS = {
       ProjectState.PREVIOUS_STATE: [ProjectState.NEW_STATE],
       ProjectState.NEW_STATE: [ProjectState.NEXT_STATE],
   }
   ```

3. **Define required deliverables**:
   ```python
   REQUIRED_DELIVERABLES = {
       ProjectState.NEW_STATE: ["deliverable1.md", "deliverable2.yaml"],
   }
   ```

4. **Add responsible agent**:
   ```python
   STATE_AGENT_MAP = {
       ProjectState.NEW_STATE: "responsible_agent",
   }
   ```

5. **Update orchestrator task builder** in `core/orchestrator.py`:
   ```python
   descriptions = {
       ProjectState.NEW_STATE: "Task description for this state",
   }
   ```

### Adding a New Message Type

**Steps**:

1. **Add to enum** in `communication/schemas.py`:
   ```python
   class MessageType(str, Enum):
       NEW_TYPE = "new_type"
   ```

2. **Create message class**:
   ```python
   class NewTypeMessage(Message):
       type: MessageType = Field(default=MessageType.NEW_TYPE, const=True)

       def __init__(self, **data):
           super().__init__(**data)
           # Validate required fields in content
   ```

3. **Add handler** in receiving components (agents, orchestrator):
   ```python
   async def _handle_message(self, message: Message):
       if message.type == MessageType.NEW_TYPE:
           await self._handle_new_type(message)
   ```

### Modifying Agent Behavior

**Guidelines**:

1. **Prefer prompt changes over code changes** when possible
2. **Edit prompts** in `prompts/` directory
3. **Test prompt changes** before committing
4. **Version control prompts** like code

**Example**: To make analyst more detailed:
- Edit `prompts/roles/analyst.md`
- Add more specific instructions
- No code changes needed

### Error Handling Pattern

**Standard pattern** used throughout:

```python
try:
    # Main logic
    result = await self.do_something()
    await self.submit_deliverable(...)
    logger.info("Success")

except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    await self._send_error(str(e), "error_type")
```

**Always**:
- Log with `exc_info=True` for stack traces
- Send error message to orchestrator
- Don't silently fail
- Include context in error messages

---

## Code Organization

### Directory Structure Philosophy

```
project/
├── agents/          # Agent implementations (domain logic)
├── core/            # Orchestration and state management
├── communication/   # Message passing infrastructure
├── memory/          # Persistence layer
├── llm/             # LLM abstraction and interaction
├── tools/           # Future: code execution, linting
├── gitops/          # Future: Git automation
├── dashboard/       # Future: Web UI
├── prompts/         # Agent prompt templates
├── artifacts/       # Generated deliverables (gitignored)
├── workspace/       # Generated code workspaces (gitignored)
└── tests/           # Future: Test suite
```

### File Naming Conventions

- **Classes**: PascalCase (`BaseAgent`, `AnalystAgent`)
- **Modules**: snake_case (`state_machine.py`, `event_bus.py`)
- **Constants**: UPPER_SNAKE_CASE (`PROJECT_STATE`, `MAX_QUEUE_SIZE`)
- **Private methods**: `_leading_underscore` (`_handle_message`)
- **Async functions**: `async def` prefix (always explicit)

### Import Organization

**Standard order**:
```python
# 1. Standard library
import asyncio
import logging
from typing import Dict, Any

# 2. Third-party
from pydantic import BaseModel

# 3. Local imports (absolute)
from core.state_machine import StateMachine
from agents.base import BaseAgent
from communication.event_bus import EventBus
```

**Never use relative imports** (`from . import foo`) - always absolute.

### Logging Convention

```python
# At module level
logger = logging.getLogger(__name__)

# In code
logger.debug("Detailed info for debugging")
logger.info("Important events, state changes")
logger.warning("Unexpected but handled situations")
logger.error("Errors that don't stop execution", exc_info=True)
logger.critical("Fatal errors")
```

**Log format**: Configured in `config.py`
- Includes timestamp, logger name, level, message
- Saved to `artifacts/system.log`

---

## Extension Points

### 1. Custom LLM Backends

**Current**: Ollama only

**To add OpenAI/Anthropic**:

1. Create new client in `llm/`:
   ```python
   class OpenAIClient(BaseLLM):
       async def generate(self, system_prompt, user_prompt, ...):
           # Implementation
   ```

2. Update factory:
   ```python
   def create_llm_for_role(role, provider="ollama"):
       if provider == "openai":
           return OpenAIClient(...)
       elif provider == "ollama":
           return OllamaClient(...)
   ```

3. Add config:
   ```python
   LLM_PROVIDER: str = Field(default="ollama", env="LLM_PROVIDER")
   ```

### 2. Code Execution Sandbox

**Planned but not implemented**

**Where to add**: `tools/code_interpreter.py`

**Interface**:
```python
class CodeInterpreter:
    def run(self, code: str, language: str) -> ExecutionResult:
        # Isolated execution
        # Return stdout, stderr, returncode
```

**Integration**: Agents can validate generated code by running it.

### 3. Vector Store for Memory

**Current**: File-based (YAML for ADRs, markdown for artifacts)

**To add ChromaDB**:

1. Update `memory/vector_store.py` (stub exists)
2. Store semantic embeddings of decisions
3. Enable semantic search across ADRs
4. Inject relevant context even if not explicitly referenced

### 4. Dashboard

**Planned but minimal**

**What to build**:
- Real-time state visualization
- Agent activity monitoring
- Artifact preview
- Event bus message history
- Manual intervention controls

**Stack**: FastAPI + WebSockets + React

**Location**: `dashboard/app.py`

### 5. Human-in-the-Loop

**Current**: Clarification requests logged but not interactive

**To implement**:

1. Add `HumanAgent` that listens for clarifications
2. Pause orchestrator when clarification needed
3. Web UI or CLI prompt for human input
4. Resume with human's answer injected

### 6. Multi-Project Support

**Current**: One project at a time

**To add**:

1. Add `project_id` to all messages and artifacts
2. Multiple orchestrator instances
3. Shared agent pool or dedicated agents per project
4. Project database/registry

---

## Common Tasks

### Testing a Single Agent

```python
# Create standalone test
import asyncio
from agents.analyst import AnalystAgent
from communication.event_bus import EventBus
from memory.adr_manager import ADRManager
from memory.artifact_store import ArtifactStore

async def test():
    bus = EventBus()
    adr_mgr = ADRManager()
    artifacts = ArtifactStore()

    agent = AnalystAgent("analyst", "analyst", bus, adr_mgr, artifacts)

    await agent.execute_task({
        "project_idea": "Simple todo app"
    })

    # Check artifacts
    spec = artifacts.retrieve("functional_spec.md")
    print(spec.read_text())

asyncio.run(test())
```

### Debugging State Transitions

```python
# In orchestrator.py, add verbose logging:

def _transition_to_state(self, new_state):
    logger.info(f"TRANSITION ATTEMPT: {self.state_machine.current_state} -> {new_state}")
    logger.info(f"Valid transitions: {self.state_machine.TRANSITIONS[self.state_machine.current_state]}")

    if self.state_machine.transition_to(new_state):
        logger.info("✓ TRANSITION SUCCESSFUL")
        # ...
    else:
        logger.error("✗ TRANSITION BLOCKED")
```

### Tracing Message Flow

```python
# In event_bus.py:

async def send(self, message):
    logger.info(f"MESSAGE: {message.from_agent} → {message.to_agent} ({message.type})")
    logger.debug(f"Content: {message.content}")
    await queue.put(message)
```

### Modifying Agent Prompts

1. Edit `prompts/roles/{agent}.md`
2. Restart system (prompts loaded at initialization)
3. Test changes
4. Commit with descriptive message

### Adding Required Deliverables

```python
# In core/state_machine.py:

REQUIRED_DELIVERABLES = {
    ProjectState.ANALYSIS: [
        "functional_spec.md",
        "user_stories.yaml",
        "risk_analysis.md"  # NEW
    ],
}
```

Then ensure agent creates this artifact.

---

## Debugging Guide

### Common Issues

#### 1. "Agent not responding"

**Symptoms**: State stuck, no deliverables

**Check**:
```bash
# Is agent running?
grep "Agent.*started" artifacts/system.log

# Did agent receive task?
grep "received task" artifacts/system.log

# Any errors?
grep "ERROR" artifacts/system.log | grep agent_name
```

**Likely causes**:
- Agent crashed (check errors)
- LLM timeout (increase `LLM_TIMEOUT`)
- Agent waiting for clarification

#### 2. "State transition failed"

**Symptoms**: Orchestrator rejects deliverable

**Check**:
```python
# In orchestrator.py:
async def _validate_deliverables(self, state):
    required = self.state_machine.get_required_deliverables(state)
    received = self.deliverables_received.get(state, [])

    logger.info(f"VALIDATION: Required={required}, Received={received}")
    # ...
```

**Likely causes**:
- Artifact not created
- Wrong artifact name
- Artifact in wrong location

#### 3. "LLM connection error"

**Symptoms**: "Connection refused" or timeout

**Check**:
```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# Is model available?
ollama list

# Test model:
ollama run qwen2.5:14b "Hello"
```

**Fix**:
```bash
ollama serve  # Start Ollama
ollama pull qwen2.5:14b  # Pull missing model
```

#### 4. "Import errors"

**Symptoms**: `ModuleNotFoundError`

**Check**:
```bash
# Correct Python?
python --version  # Must be 3.11+

# Dependencies installed?
pip list | grep pydantic

# Virtual environment activated?
which python
```

**Fix**:
```bash
pip install -r requirements.txt
```

### Debug Logging

**Enable verbose logging**:

```python
# In config.py or .env:
LOG_LEVEL=DEBUG
```

Or programmatically:
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Inspecting Event Bus

```python
# Get statistics:
stats = event_bus.get_stats()
print(f"Total messages: {stats['total_messages']}")
print(f"Queue sizes: {stats['queue_sizes']}")

# Get message history:
history = event_bus.get_history(limit=10)
for msg in history:
    print(f"{msg.from_agent} → {msg.to_agent}: {msg.type}")
```

### Inspecting ADRs

```python
# List all ADRs:
adrs = adr_manager.list_all()
for adr in adrs:
    print(f"{adr.id}: {adr.title} ({adr.status})")

# Check constraints:
constraints = adr_manager.get_constraints_summary()
print(constraints)
```

---

## What's Complete vs. What's Not

### ✅ Complete and Production-Ready

1. **Core Architecture**
   - Event bus with async messaging
   - State machine with validation
   - Orchestrator workflow management
   - Base agent framework

2. **Memory Management**
   - ADR system (create, store, query, accept)
   - Artifact store (organized storage)
   - Decision persistence

3. **LLM Integration**
   - Ollama client (async)
   - Factory pattern
   - Role-specific model selection
   - Error handling and retries

4. **Specialized Agents**
   - Analyst (functional specs, user stories)
   - Architect (architecture, API specs, ADRs)
   - CTO Reviewer (comprehensive review)
   - Designer, Backend, Frontend, QA (simplified but functional)

5. **Configuration**
   - Pydantic settings
   - Environment variable support
   - Logging configuration

6. **Documentation**
   - Setup guide
   - README
   - This developer guide

### ⚠️ Implemented but Simplified

1. **Specialized Agents** (Designer, Backend, Frontend, QA)
   - Work correctly but generate plans, not actual code
   - Could be enhanced to generate real implementation

2. **Error Recovery**
   - Errors logged and reported
   - No automatic retry or state rollback
   - No human escalation flow

3. **Validation**
   - Basic deliverable presence checking
   - No deep content validation
   - No schema validation for artifacts

### ❌ Not Implemented (Planned)

1. **Code Execution Sandbox**
   - `tools/code_interpreter.py` exists but is a stub
   - No actual code execution or validation
   - **Impact**: Agents can't verify code works

2. **GitOps Automation**
   - `gitops/` directory exists
   - No automatic branch creation per task
   - No PR generation
   - **Impact**: Manual git operations needed

3. **Web Dashboard**
   - `dashboard/` directory exists
   - No real-time UI
   - No monitoring interface
   - **Impact**: Must monitor via logs

4. **Human-in-the-Loop**
   - Clarification requests logged but not interactive
   - No pause/resume mechanism
   - No approval workflows
   - **Impact**: System runs fully autonomous (good and bad)

5. **Vector Store**
   - `memory/vector_store.py` exists but minimal
   - No semantic search
   - No embedding-based context retrieval
   - **Impact**: Context limited to explicit ADR queries

6. **Testing Suite**
   - No unit tests
   - No integration tests
   - No mocks for LLM
   - **Impact**: Manual testing required

7. **Multi-Project Support**
   - Single project at a time
   - No project database
   - No concurrent projects
   - **Impact**: Run sequentially

8. **Actual Code Generation**
   - Agents plan but don't write full code
   - No file scaffolding
   - No code templates
   - **Impact**: Generates designs, not runnable apps

---

## Known Limitations

### 1. LLM Quality Dependency

**Issue**: Output quality depends entirely on LLM capabilities.

**Mitigation**:
- Use high-quality models (qwen2.5:14b, deepseek-coder)
- Prompt engineering in templates
- ADR constraints limit drift

**Not solved**: Bad LLM = bad output

### 2. No Code Verification

**Issue**: Agents can suggest code that doesn't compile/run.

**Mitigation**: CTO reviewer can catch obvious issues

**Not solved**: Need code interpreter (planned)

### 3. Context Window Limits

**Issue**: Large projects may exceed LLM context windows.

**Mitigation**:
- ADRs provide summary of decisions
- Artifacts truncated when passed to agents

**Not solved**: Very large projects may still overflow

### 4. Sequential Processing

**Issue**: States execute sequentially, not in parallel.

**Mitigation**: Agents run concurrently within a state

**Not solved**: Can't parallelize across states (Design + Implementation at same time)

### 5. No Streaming Output

**Issue**: Must wait for complete LLM response.

**Mitigation**: Async allows other work during generation

**Not solved**: No progress indicators during generation

### 6. Determinism Challenges

**Issue**: LLM outputs vary slightly between runs.

**Mitigation**:
- Temperature = 0.0 for most agents
- ADRs lock in decisions

**Not solved**: Exact reproducibility not guaranteed

---

## Future Improvements

### Priority 1: High Impact, Feasible

1. **Code Interpreter**
   - Execute code in sandbox
   - Validate compilations
   - Run tests automatically
   - **Benefit**: Catch errors early

2. **Comprehensive Testing**
   - Unit tests for all modules
   - Integration tests for workflows
   - Mock LLM for fast tests
   - **Benefit**: Confidence in changes

3. **Human Approval Gates**
   - Pause before major decisions
   - Web UI for approval
   - Resume after approval
   - **Benefit**: Human control when needed

4. **Enhanced Agents**
   - Backend: Generate actual FastAPI code
   - Frontend: Generate React components
   - Full file scaffolding
   - **Benefit**: Runnable output

### Priority 2: Nice to Have

5. **Web Dashboard**
   - Real-time state visualization
   - Agent activity monitoring
   - Artifact preview
   - **Benefit**: Better visibility

6. **Vector Store Integration**
   - Semantic search across ADRs
   - Context retrieval by similarity
   - **Benefit**: Better context management

7. **Multi-Model Support**
   - OpenAI API option
   - Anthropic Claude option
   - Model switching per agent
   - **Benefit**: Flexibility

8. **GitOps Automation**
   - Auto-create branches
   - Auto-generate PRs
   - CI/CD integration
   - **Benefit**: True DevOps flow

### Priority 3: Advanced

9. **Multi-Project Support**
   - Project database
   - Concurrent projects
   - Resource allocation
   - **Benefit**: Scalability

10. **Agent Learning**
    - Fine-tune on project history
    - Learn from corrections
    - Personalized behavior
    - **Benefit**: Continuous improvement

11. **Security Hardening**
    - Sandbox all operations
    - Input validation
    - Rate limiting
    - Audit logs
    - **Benefit**: Production security

12. **Performance Optimization**
    - Cache LLM responses
    - Parallel state execution
    - Streaming responses
    - **Benefit**: Faster execution

---

## Development Workflow

### Making Changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Follow existing patterns
   - Update prompts if changing behavior
   - Add logging for new functionality

3. **Test manually**:
   ```bash
   python main.py "Simple test project"
   # Verify output in artifacts/
   ```

4. **Commit with descriptive message**:
   ```bash
   git add .
   git commit -m "Add feature: description

   - Detail 1
   - Detail 2

   Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
   ```

5. **Merge to main**:
   ```bash
   git checkout main
   git merge feature/your-feature-name --no-ff
   ```

### Debugging Workflow

1. **Reproduce issue**
2. **Add debug logging**
3. **Run with DEBUG=true**
4. **Examine logs**
5. **Fix and verify**
6. **Remove debug logging**
7. **Commit fix**

### Prompt Engineering Workflow

1. **Identify agent behavior to change**
2. **Edit prompt in `prompts/`**
3. **Restart system** (prompts load at init)
4. **Test with simple project**
5. **Iterate until desired behavior**
6. **Commit prompt changes**

---

## Communication Protocol

### Message Flow Example

```
Human: "Create a todo app"
  ↓
main.py: Create AITeam, call run_project()
  ↓
Orchestrator: start_project() → State = ANALYSIS
  ↓
Orchestrator: Send TaskMessage → analyst
  ↓
Analyst: Receive task, load ADRs
  ↓
Analyst: generate_response() → LLM
  ↓
Analyst: Store artifacts, send DeliverableMessage → orchestrator
  ↓
Orchestrator: Validate deliverables
  ↓
Orchestrator: State = ARCHITECTURE
  ↓
[Repeat for each state...]
  ↓
CTO: Review complete, decision = GO
  ↓
Orchestrator: State = DELIVERY
  ↓
System: Print final status, exit
```

### Message Anatomy

```python
{
  "from_agent": "analyst",
  "to_agent": "orchestrator",
  "type": "deliverable",
  "content": {
    "summary": "Functional analysis complete",
    "artifacts": ["functional_spec.md", "user_stories.yaml"],
    "phase": "analysis"
  },
  "blocking": false,
  "priority": "medium",
  "timestamp": "2026-01-01T12:34:56"
}
```

---

## Key Files Reference

### Most Important Files (Read These First)

1. **`main.py`** - Entry point, understand system initialization
2. **`core/orchestrator.py`** - Brain of the system
3. **`core/state_machine.py`** - Workflow definition
4. **`agents/base.py`** - Agent framework
5. **`communication/event_bus.py`** - Message passing
6. **`config.py`** - Configuration

### Extend These Often

1. **`prompts/roles/*.md`** - Agent behavior
2. **`agents/`** - New agents or enhanced agents
3. **`core/state_machine.py`** - Add states
4. **`config.py`** - Add settings

### Rarely Change

1. **`communication/schemas.py`** - Message protocol (stable)
2. **`llm/base.py`** - LLM interface (stable)
3. **`memory/adr_manager.py`** - ADR system (stable)

---

## Conventions to Maintain

1. **Always use async/await** for I/O operations
2. **Always log important events** (state changes, deliverables, errors)
3. **Always validate inputs** with Pydantic
4. **Always use type hints** for function signatures
5. **Always submit deliverables** through orchestrator (no direct storage)
6. **Always load ADRs** before agent acts
7. **Always handle exceptions** and report errors
8. **Never hardcode prompts** in Python code
9. **Never skip state validation**
10. **Never communicate outside event bus**

---

## Final Notes for AI Continuity

### Philosophy

This system embodies the principle: **"The whole is greater than the sum of its parts."**

Individual agents are simple, but coordinated through:
- Structured communication
- Shared memory (ADRs)
- State-driven workflow
- Governance rules

They achieve complex software development autonomously.

### Approach for Changes

1. **Understand before changing**: Read relevant sections of this guide
2. **Maintain patterns**: Follow existing conventions
3. **Test incrementally**: Small changes, frequent testing
4. **Document decisions**: Update this guide when making architectural changes
5. **Think holistically**: Changes ripple through the system

### When Stuck

1. Check logs: `artifacts/system.log`
2. Review this guide: Search for relevant section
3. Trace message flow: Add debug logging
4. Test components individually: Create small test scripts
5. Refer to SOC.txt: Original requirements and context

### Success Metrics

The system is working well when:
- ✅ Projects progress through all states
- ✅ All required artifacts are generated
- ✅ ADRs are created and respected
- ✅ CTO review provides meaningful feedback
- ✅ No unhandled exceptions in logs
- ✅ Agents complete tasks without hanging

### Contact Points for Questions

- **Original conversation**: `SOC.txt` - Requirements and context
- **This guide**: Architecture and implementation
- **Setup guide**: `SETUP.md` - User-facing instructions
- **Code comments**: Inline documentation
- **Git history**: `git log` - Evolution of decisions

---

**This guide should enable any AI agent to continue development effectively. When in doubt, preserve existing patterns and consult this document.**

**Version**: 1.0
**Last Updated**: 2026-01-01
**Authors**: Claude Sonnet 4.5
**Status**: Production-Ready Foundation
