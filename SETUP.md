# AI Software Engineering Team - Setup Guide

Complete setup instructions for running your autonomous AI software engineering team.

## Prerequisites

### Required Software

1. **Python 3.11 or higher**
   ```bash
   python --version  # Should show 3.11+
   ```

2. **Ollama** (for local LLM inference)
   - Visit https://ollama.ai
   - Download and install for your platform
   - Verify installation:
     ```bash
     ollama --version
     ```

3. **Git** (already initialized)
   ```bash
   git --version
   ```

## Step 1: Install Ollama Models

The system uses different models optimized for different roles:

```bash
# Reasoning models (analyst, architect, cto)
ollama pull qwen2.5:14b

# Code generation models (backend, frontend)
ollama pull deepseek-coder:6.7b

# Creative/testing models (designer, qa)
ollama pull mistral:7b
```

**Note**: These downloads can be large (several GB each). Ensure you have:
- At least 20GB free disk space
- Good internet connection
- Time for downloads (10-30 minutes depending on connection)

### Verify Ollama is Running

```bash
# Start Ollama (if not already running)
ollama serve

# In another terminal, test:
ollama list  # Should show your downloaded models
```

## Step 2: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

### If you encounter issues:

```bash
# Create a virtual environment first (recommended)
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Then install dependencies
pip install -r requirements.txt
```

## Step 3: Configuration (Optional)

The system works with default settings, but you can customize via environment variables or a `.env` file.

### Create a `.env` file (optional):

```bash
# LLM Configuration
OLLAMA_HOST=http://localhost:11434
LLM_TIMEOUT=120

# Logging
LOG_LEVEL=INFO
DEBUG=false

# Custom model selection (optional)
MODEL_ANALYST=qwen2.5:14b
MODEL_ARCHITECT=qwen2.5:14b
MODEL_BACKEND=deepseek-coder:6.7b
MODEL_FRONTEND=deepseek-coder:6.7b
MODEL_DESIGNER=mistral:7b
MODEL_QA=mistral:7b
MODEL_CTO=qwen2.5:14b
```

## Step 4: Verify Setup

Run a quick health check:

```bash
# Check if Ollama is accessible
curl http://localhost:11434/api/tags

# You should see a JSON response with your models
```

## Step 5: Run Your First Project

### Quick Start - Default Todo API

```bash
python main.py
```

This will run the default test project (a simple Todo API).

### Custom Project

```bash
python main.py "Your project idea goes here. Be as detailed as you want."
```

Example:
```bash
python main.py "Create a blog platform with user authentication, post creation, commenting, and markdown support"
```

## What to Expect

When you run the system, you'll see:

1. **Initialization**: All agents start up
2. **Project Start**: Orchestrator receives the idea
3. **State Transitions**: The project moves through states:
   - ANALYSIS → Analyst creates specs and user stories
   - ARCHITECTURE → Architect designs system and creates ADRs
   - DESIGN → Designer creates design system
   - IMPLEMENTATION → Backend and Frontend create implementation plans
   - TESTING → QA creates test plans and results
   - REVIEW → CTO performs final review
   - DELIVERY → Project complete!

4. **Artifacts**: Check `artifacts/` directory for all generated documents

### Monitoring Progress

Watch the console output for:
- State transitions
- Agent activities
- Deliverable submissions
- Any errors or clarification requests

### Logs

Detailed logs are saved to:
- `artifacts/system.log` - Full system log
- Console output - Key events and progress

## Troubleshooting

### "Connection Error" when starting

**Problem**: Cannot connect to Ollama

**Solution**:
```bash
# Make sure Ollama is running
ollama serve

# Check it's accessible
curl http://localhost:11434/api/tags
```

### "Model not found"

**Problem**: Required model not downloaded

**Solution**:
```bash
# Pull missing model
ollama pull qwen2.5:14b
ollama pull deepseek-coder:6.7b
ollama pull mistral:7b

# Verify
ollama list
```

### "Module not found" errors

**Problem**: Python dependencies not installed

**Solution**:
```bash
pip install -r requirements.txt

# If still failing, ensure you're in the right environment
python --version  # Check Python version
which python      # Check which Python you're using
```

### Slow performance

**Tips**:
- Ollama models run faster on systems with good RAM (16GB+)
- First run with each model may be slower (model loading)
- Smaller models (7b) are faster than larger ones (14b)

**Alternatives**:
```bash
# Use smaller, faster models if needed
export MODEL_ANALYST=mistral:7b
export MODEL_ARCHITECT=mistral:7b
export MODEL_CTO=mistral:7b
python main.py
```

### System hangs or timeouts

**Check**:
- Is Ollama running and responsive?
- Do you have enough system resources?
- Check logs in `artifacts/system.log`

**If stuck**, interrupt with `Ctrl+C` and check logs for errors.

## Examining Results

After a successful run:

```bash
# View all generated artifacts
ls -la artifacts/

# View specific documents
cat artifacts/analysis/functional_spec.md
cat artifacts/architecture/architecture.md
cat artifacts/review/cto_review.md

# View ADRs
cat artifacts/adrs/ADR-001.yaml
```

## Advanced Usage

### Running Specific Scenarios

```bash
# E-commerce platform
python main.py "Create a full e-commerce platform with product catalog, shopping cart, checkout, and order management"

# Social network
python main.py "Create a social networking application with user profiles, posts, comments, likes, and friend connections"

# DevOps tool
python main.py "Create a CI/CD pipeline dashboard that monitors builds, deployments, and test results"
```

### Customizing Agent Behavior

Edit prompt templates in `prompts/` directory:
- `prompts/global/system.md` - Rules for all agents
- `prompts/roles/*.md` - Role-specific prompts
- `prompts/review/cto.md` - CTO review criteria

### Accessing Agent Logs

Each agent logs its activities. Filter logs by agent name:

```bash
# View analyst logs only
grep "analyst" artifacts/system.log

# View orchestrator decisions
grep "orchestrator" artifacts/system.log | grep "transition"
```

## Next Steps

Once setup is complete:

1. **Test with simple projects** - Start with the default Todo API
2. **Try custom projects** - Provide your own ideas
3. **Examine artifacts** - See what the agents produced
4. **Adjust prompts** - Customize agent behavior
5. **Experiment with models** - Try different LLM models

## Getting Help

If you encounter issues:

1. Check logs in `artifacts/system.log`
2. Verify Ollama is running: `ollama list`
3. Check Python dependencies: `pip list`
4. Review this setup guide

## System Architecture

Quick overview of how it works:

```
main.py
  ├── Orchestrator (manages workflow)
  ├── Event Bus (agent communication)
  ├── Memory Manager (ADRs, artifacts)
  └── Agents (analyst, architect, designer, backend, frontend, qa, cto)
```

Each agent:
- Receives tasks from orchestrator
- Uses LLM to generate output
- Stores artifacts
- Submits deliverables
- Respects ADRs (architectural decisions)

## Performance Tips

- **First run**: Slower (model loading)
- **Subsequent runs**: Faster (models cached)
- **RAM**: More is better (16GB+ recommended)
- **CPU**: More cores help with concurrent operations
- **Storage**: SSD recommended for model storage

Enjoy your autonomous AI software engineering team!
