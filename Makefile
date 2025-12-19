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



#################################################################################
# CLEANUP TARGETS                                                               #
#################################################################################

CLEAN_DIRS := .pytest_cache .ruff_cache .mypy_cache .logs_queue .nux .mkdocs
EGG_INFO   := *.egg-info
CONFIRM_MSG = 🔴 This will delete permanently! Confirm with "$(1)" or pass


## Remove Python compiled files and build artifacts
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	for dir in $(CLEAN_DIRS); do \
		find . -type d -name "$dir" -exec rm -rf {} + 2>/dev/null || true; \
	done
	find . -type d -name "$(EGG_INFO)" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".tmp*" -exec rm -rf {} + 2>/dev/null || true
	[ -d data ] && find data -depth -type d -empty -delete 2>/dev/null || true
	[ -d logs ] && find logs -depth -type d -empty -delete 2>/dev/null || true

## Remove virtual environment (requires confirmation)
.PHONY: purge-venv
purge-venv:
	@echo "$(call CONFIRM_MSG,venv)"
	@read ans; \
	case "$$ans" in \
		venv) rm -rf .venv ;; \
		*) echo "❌ Canceled." ;; \
	esac

## Remove application logs (requires confirmation)
.PHONY: purge-logs
purge-logs:
	@echo "$(call CONFIRM_MSG,logs)"
	@read ans; \
	case "$$ans" in \
		logs) \
			find . -type f -name "*.log" -delete 2>/dev/null || true; \
			rm -rf logs/* 2>/dev/null || true ;; \
		*) echo "❌ Canceled." ;; \
	esac

## Remove nginx logs (requires confirmation and sudo)
.PHONY: purge-nginx-logs
purge-nginx-logs:
	@echo "$(call CONFIRM_MSG,nginx)"
	@read ans; \
	case "$$ans" in \
		nginx) rm -rf .nginx/logs ;; \
		*) echo "❌ Canceled." ;; \
	esac

## Remove user data directory (requires confirmation)
.PHONY: purge-data
purge-data:
	@echo "$(call CONFIRM_MSG,data)"
	@read ans; \
	case "$$ans" in \
		data) rm -rf data/* 2>/dev/null || true ;; \
		*) echo "❌ Canceled." ;; \
	esac
	
## Remove tailscale data (requires confirmation and sudo)
# purge-tailscale:
# 	@echo "$(call CONFIRM_MSG,tailscale)"
# 	@read ans; \
# 	case "$$ans" in \
# 		tailscale) sudo rm -rf .tailscale/data ;; \
# 		*) echo "❌ Canceled." ;; \
# 	esac

## Nuclear option: purge everything (confirms each target)
purge-all: clean purge-venv purge-logs purge-nginx-logs purge-data

#################################################################################
# DOCUMENTATION                                                                 #
#################################################################################

.PHONY: docs-up docs-watch docs-build docs-deploy

## Serve documentation locally
docs-up:
	@echo ">>> Serving documentation on http://localhost:8000"
	mkdocs serve -a 0.0.0.0:8000

## Watch files and serve documentation
docs-watch:
	@echo ">>> Watching files and serving..."
	find docs/ drugslm/ -type f \( -name "*.py" -o -name "*.md" \) | entr -r mkdocs serve -a 0.0.0.0:8000

## Build static documentation
docs-build:
	@echo ">>> Building static site..."
	mkdocs build -d .nginx/www/docs/

## Deploy to GitHub Pages
docs-deploy:
	@echo ">>> Deploying to GitHub Pages..."
	mkdocs gh-deploy --force


#################################################################################
# HELPER - Execution Context Check                                              #
#################################################################################
# Macro to detect if the make command is running inside a Docker container.
# It checks for the existence of the /.dockerenv file (standard in containers).
define BLOCK_IN_DOCKER
	@if [ -f /.dockerenv ]; then \
		echo "❌ ERROR: The command '$(MAKECMDGOALS)' cannot be run inside a container."; \
		echo "   -> Please exit the container (type 'exit') and run this from your Host machine."; \
		exit 1; \
	fi
endef

# TODO: Think in
# - docker-funnel: docker compose up funnel nginx chat mkdocs
#################################################################################
# DOCKER CONTROLLER - Only Cleanup                                              #
#################################################################################
.PHONY: docker-down docker-clean docker-purge

# Gets the current folder name to use as the project name
# PROJECT := $(notdir $(CURDIR))
# 	docker compose -p $(PROJECT) down --rmi all --remove-orphans

docker-down:
	$(BLOCK_IN_DOCKER)
# 	@echo "Stopping containers..."
	docker compose -p $(COMPOSE_PROJECT_NAME) down
	@echo

docker-clean:
	$(BLOCK_IN_DOCKER)
# 	@echo "🧹 Cleaning up containers, networks, and images..."
	docker compose -p $(COMPOSE_PROJECT_NAME) down --rmi all --remove-orphans
	@echo

docker-purge:
	$(BLOCK_IN_DOCKER)
	@echo "🔴 WARNING: You are about to delete containers, images, and PERSISTENT VOLUMES."
	@echo -n "Type '$(COMPOSE_PROJECT_NAME)' to confirm ( or anything to cancel ): "; \
	read ans; \
	if [ "$$ans" != "$(COMPOSE_PROJECT_NAME)" ]; then \
		echo "❌ Canceled. Confirmation failed."; \
		exit 1; \
	fi
# 	@echo "🔥 Purging everything..."
	docker compose -p $(COMPOSE_PROJECT_NAME) down --rmi all --volumes --remove-orphans
	@echo

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
