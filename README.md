# AI Software Engineering Team

An autonomous multi-agent system for software development, powered by open-source LLMs.

## Overview

This system creates a virtual software engineering team composed of specialized AI agents that can autonomously develop applications from ideas to delivery.

### Team Members

- **Functional Analyst**: Transforms ideas into clear specifications and user stories
- **Solution Architect**: Designs system architecture and makes technical decisions
- **Backend Developer**: Implements backend services (Python/FastAPI)
- **Frontend Developer**: Builds user interfaces (React/TypeScript)
- **UI/UX Designer**: Creates user experience and wireframes
- **QA Engineer**: Tests and validates functionality
- **CTO Reviewer**: Provides final architecture and security review

### Key Features

- **Autonomous Operation**: Agents communicate and collaborate without constant human intervention
- **Memory Management**: ADR (Architecture Decision Records) system prevents context loss
- **GitOps**: Automatic branch creation, testing, and merging
- **Web Dashboard**: Real-time monitoring of project state
- **Open Source LLMs**: Uses Ollama for local, private operation
- **Governance**: Strict rules and validation prevent hallucinations

## Project Workflow

```
IDEA → ANALYSIS → ARCHITECTURE → DESIGN → IMPLEMENTATION → TESTING → REVIEW → DELIVERY
```

## Installation

### Prerequisites

- Python 3.11+
- Ollama (for local LLM inference)
- Git

### Setup

1. Install Ollama:
```bash
# Visit https://ollama.ai for installation instructions
```

2. Pull required models:
```bash
ollama pull qwen2.5:14b       # For analyst and architect
ollama pull deepseek-coder:6.7b  # For developers
ollama pull mistral:7b        # For designer and QA
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Start the system:

```bash
# Terminal 1: Start the dashboard
uvicorn dashboard.app:app --reload

# Terminal 2: Run the agent system
python main.py
```

### Access the dashboard:
Open http://localhost:8000 in your browser

## Architecture

```
┌─────────────────────┐
│   Orchestrator      │ ← Manages workflow and state transitions
├─────────────────────┤
│    Event Bus        │ ← Agent communication
├─────────────────────┤
│  Memory Manager     │ ← ADR storage and retrieval
├─────────────────────┤
│  Agent Pool         │ ← Specialized agents
└─────────────────────┘
```

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Agents

1. Create a prompt template in `prompts/roles/`
2. Implement the agent class in `agents/`
3. Register in the orchestrator

## Configuration

Edit `config.py` to customize:
- LLM models per role
- Ollama host
- Workflow states
- Dashboard settings

## License

MIT
