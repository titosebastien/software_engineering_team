.PHONY: help venv deps run ollama-serve ollama-check ollama-models ollama-warm ollama-ready

VENV ?= venv
PYTHON ?= $(VENV)/bin/python
PIP ?= $(VENV)/bin/pip

# Default model names mirror config.py; override via env or `make MODEL_ANALYST=...`
MODEL_ANALYST ?= qwen2.5:14b
MODEL_ARCHITECT ?= qwen2.5:14b
MODEL_BACKEND ?= deepseek-coder:6.7b
MODEL_FRONTEND ?= deepseek-coder:6.7b
MODEL_DESIGNER ?= mistral:7b
MODEL_QA ?= mistral:7b
MODEL_CTO ?= qwen2.5:14b

MODELS ?= $(sort $(MODEL_ANALYST) $(MODEL_ARCHITECT) $(MODEL_BACKEND) $(MODEL_FRONTEND) $(MODEL_DESIGNER) $(MODEL_QA) $(MODEL_CTO))

help:
	@echo "make ollama-serve   - start the Ollama server"
	@echo "make ollama-check   - verify Ollama is reachable"
	@echo "make ollama-models  - pull required models for main_crewai"
	@echo "make ollama-warm    - load required models into Ollama"
	@echo "make ollama-ready   - check Ollama, pull, and warm models"
	@echo "make run            - ensure env, deps, models, then run main_crewai"

venv:
	@test -d $(VENV) || virtualenv venv

deps: venv
	@$(PIP) install -r requirements-crewai.txt

ollama-serve:
	@ollama serve

ollama-check:
	@ollama list >/dev/null
	@echo "Ollama is running."

ollama-models:
	@for m in $(MODELS); do \
		echo "Pulling $$m"; \
		ollama pull $$m; \
	done

ollama-warm: ollama-check
	@for m in $(MODELS); do \
		echo "Warming $$m"; \
		ollama run $$m "warmup" >/dev/null; \
	done

ollama-ready: ollama-check ollama-models ollama-warm
	@echo "Ollama models ready for main_crewai."

run: deps ollama-ready
	@$(PYTHON) main_crewai.py
