#################################################################################
# GLOBALS                                                                       #
#################################################################################

PYTHON = python
UV = uv

# Load business variables (VERSION, passwords, etc)
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

VENV_PATH := .venv
LOCKFILE := uv.lock

#################################################################################
# ENVIRONMENT & DEPENDENCY MANAGEMENT                                           #
#################################################################################

# Ensure make sees uv immediately after installation
export PATH := $(HOME)/.local/bin:$(PATH)

## Toolchain: Install uv (System level, no root required)
.PHONY: install
install:
	@echo ">>> Checking system requirements..."
	@command -v uv >/dev/null 2>&1 || (echo ">>> Installing uv..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo ">>> Toolchain ready (uv installed)."
	@echo ""
	@echo "======================================================================"
	@echo "  NEXT STEPS: Shell Configuration"
	@echo "----------------------------------------------------------------------"
	@echo "  To configure your shell permanently, run one of the commands below"
	@echo "  and append the output to your config file (e.g., ~/.bashrc):"
	@echo ""
	@echo 'export PATH="$$HOME/.local/bin:$$PATH"'
	@echo 'eval "$$(uv generate-shell-completion bash)"'
	@echo 'eval "$$(uvx --generate-shell-completion bash)"'
	@echo ""
	@echo "======================================================================"


## Environment configuration options
.PHONY: info
info:
	@echo ""
	@echo "======================================================================"
	@echo "  ENVIRONMENT CONFIGURATION OPTIONS"
	@echo "----------------------------------------------------------------------"
	@echo ""
	@echo "  1. Nested Shell (Easiest):"
	@echo "     Run 'uv run bash' to spawn a configured shell inside the environment."
	@echo ""
	@echo "  2. Manual Activation (Current Shell):"
	@echo "     Run 'source $(VENV_PATH)/bin/activate' to activate in your current terminal."
	@echo ""
	@echo "  3. Auto-Activation (Recommended for Persistent):"
	@echo "     Add the activation command to your shell config file:"
	@echo "     echo 'source $$(pwd)/$(VENV_PATH)/bin/activate' >> ~/.bashrc"
	@echo ""
	@echo "  4. Standalone Command:"
	@echo "     Run python commands that depend on the environment without having to activate it using:"
	@echo "      - uv run python -m module" or 
	@echo "      - uv run module"
	@echo ""
	@echo "======================================================================"
	@echo ""


## Install only main dependencies (Locked, No Dev/Docs)
.PHONY: build
build:
	@echo ">>> Production build: main dependencies only."
	$(MAKE) sync-prod

## Install EVERYTHING (Main + All Extras/Groups)
.PHONY: dev
dev:
	@echo ">>> Setting up full development environment..."
	$(MAKE) sync-dev
	$(MAKE) info

# Generate lock for dev and prod. The lockfile is always total
.PHONY: lock
lock:
	@echo ">>> Creating a full lockfile based on pyproject..."
	@rm -f $(LOCKFILE)
	uv lock

# Sync development environment using the lockfile (fallback included)
.PHONY: sync-dev
sync-dev:
	@echo ">>> Syncing full development environment..."
	@if uv sync --locked --all-extras --all-groups; then \
	    echo ">>> Dev sync OK (using lockfile)."; \
	else \
	    echo ">>> Lockfile missing or invalid. Rebuilding lock..."; \
	    $(MAKE) lock; \
	    uv sync --locked --all-extras --all-groups; \
	fi

# Sync production environment using the lockfile (fallback included)
.PHONY: sync-prod
sync-prod:
	@echo ">>> Syncing production environment..."
	@if uv sync --locked --no-dev; then \
	    echo ">>> Prod sync OK (using lockfile)."; \
	else \
	    echo ">>> Lockfile missing or invalid. Rebuilding lock..."; \
	    $(MAKE) lock; \
	    uv sync --locked --no-dev; \
	fi

## Check environment info
.PHONY: test-env
test-env:
	uv run $(PYTHON) --version
	uv run $(PYTHON) -c "import sys; print(f'Python executing from: {sys.executable}')"
	uv run $(PYTHON) -c "import drugslm; print(f'{drugslm}')"

#################################################################################
# CODE QUALITY & TESTING                                                        #
#################################################################################

## Lint using ruff (check only)
.PHONY: lint
lint:
	uv run ruff format --check
	uv run ruff check

## Format source code with ruff (fix violations)
.PHONY: format
format:
	uv run ruff check --fix
	uv run ruff format

## Run tests
.PHONY: test
test:
	uv run pytest tests

## Delete all compiled Python files, build artifacts and caches
.PHONY: clean
clean:
	@echo ">>> Delete all compiled Python files, build artifacts and caches"
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".logs_queue" -exec rm -rf {} +
	find . -type d -name ".nux" -exec rm -rf {} +
	find . -type d -name ".tmp*" -exec rm -rf {} +

	@echo ">>> Project cleanup completed"


## Delete all not trackerable files, include .venv, less .env 
## In future, ask for confirmation for each remove
.PHONY: purge
purge: clean
	@echo ""
	@echo ">>> Delete all not trackerable files, include .venv (less .env)"
	find . -type d -name ".venv" -exec rm -rf {} +
	rm -rf site
	@echo ">>> Project purge completed"

#################################################################################
# DAGSTER CONTROLLER                                                            #
#################################################################################

# Detect if the target is "dagster"
ifeq (dagster,$(firstword $(MAKECMDGOALS)))
  DAGSTER_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(DAGSTER_ARGS):;@:)
endif

## Manage Dagster environment (Args: up, down, restart, clean)
.PHONY: dagster
dagster:
	@if [ -z "$(DAGSTER_ARGS)" ]; then \
		echo "Usage: make dagster [COMMAND]"; \
		echo ""; \
		echo "Commands:"; \
		echo "  up       Start Dagster dev server (0.0.0.0:3000)"; \
		echo "  down     Stop Dagster dev server"; \
		echo "  restart  Restart the server"; \
		echo "  clean    Clean Dagster storage (runs, schedules)"; \
		echo ""; \
	elif [ "$(DAGSTER_ARGS)" = "up" ]; then \
		echo ">>> Starting Dagster..."; \
		uv run dagster dev -h 0.0.0.0 -p 3000; \
	elif [ "$(DAGSTER_ARGS)" = "down" ]; then \
		echo ">>> Stopping Dagster..."; \
		pkill -f "dagster dev" || echo "Dagster not running"; \
	elif [ "$(DAGSTER_ARGS)" = "restart" ]; then \
		$(MAKE) dagster down; \
		$(MAKE) dagster up; \
	elif [ "$(DAGSTER_ARGS)" = "clean" ]; then \
		rm -rf .dagster/storage/*; \
		rm -rf .logs_queue; \
		mkdir -p .dagster/storage; \
		echo ">>> Dagster storage cleaned"; \
	else \
		echo "Unknown command: '$(DAGSTER_ARGS)'"; \
		exit 1; \
	fi

#################################################################################
# DOCUMENTATION CONTROLLER                                                      #
#################################################################################

# Detect if the target is "docs"
ifeq (docs,$(firstword $(MAKECMDGOALS)))
  DOCS_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(DOCS_ARGS):;@:)
endif

## Manage Documentation (Args: up, down, restart, build, deploy)
.PHONY: docs
docs:
	@if [ -z "$(DOCS_ARGS)" ]; then \
		echo "Usage: make docs [COMMAND]"; \
		echo ""; \
		echo "Commands:"; \
		echo "  up       Serve documentation locally (0.0.0.0:8000)"; \
		echo "  watch    Watch files with entr and serve documentation locally (0.0.0.0:8000)"; \
		echo "  down     Stop documentation server"; \
		echo "  restart  Restart the documentation server"; \
		echo "  build    Build static documentation to site/"; \
		echo "  deploy   Deploy documentation to GitHub Pages"; \
		echo ""; \
	elif [ "$(DOCS_ARGS)" = "up" ]; then \
		echo ">>> Serving documentation..."; \
		echo "mkdocs serve -a 0.0.0.0:8000"; \
		mkdocs serve -a 0.0.0.0:8000; \
	elif [ "$(DOCS_ARGS)" = "watch" ]; then \
		echo ">>> Serving documentation..."; \
		echo "find docs/ drugslm/ -type f \( -name "*.py" -o -name "*.md" \) | entr -r mkdocs serve -a 0.0.0.0:8000"; \
		find docs/ drugslm/ -type f \( -name "*.py" -o -name "*.md" \) | entr -r mkdocs serve -a 0.0.0.0:8000; \
	elif [ "$(DOCS_ARGS)" = "down" ]; then \
		echo ">>> Stopping documentation server..."; \
		pkill -f "mkdocs serve" || echo "Mkdocs not running"; \
	elif [ "$(DOCS_ARGS)" = "restart" ]; then \
		$(MAKE) docs down; \
		$(MAKE) docs up; \
	elif [ "$(DOCS_ARGS)" = "build" ]; then \
		mkdocs build -f mkdocs.yaml; \
	elif [ "$(DOCS_ARGS)" = "deploy" ]; then \
		mkdocs gh-deploy; \
	else \
		echo "Unknown command: '$(DOCS_ARGS)'"; \
		exit 1; \
	fi

#################################################################################
# START CONTROLLER                                                              #
#################################################################################

## Sleep infinity (Useful for keeping container alive for attaching)
.PHONY: sleep
sleep:
	@echo "sleeping infinity waiting for attach"
	sleep infinity

#################################################################################
# SELF DOCUMENTING COMMANDS                                                     #
#################################################################################

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys; \
lines = '\n'.join([line for line in sys.stdin]); \
matches = re.findall(r'\n## (.*)\n[\s\S]+?\n([a-zA-Z_-]+):', lines); \
print('Available rules:\n'); \
print('\n'.join(['{:25}{}'.format(*reversed(match)) for match in matches]))
endef
export PRINT_HELP_PYSCRIPT

help:
	@uv run $(PYTHON) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)
