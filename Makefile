#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = drugslm
PYTHON_VERSION = 3.12
PYTHON_INTERPRETER = python
UV = uv

#################################################################################
# COMMANDS                                                                      #
#################################################################################

## Install dependencies (Locked - Production/CI safe)
.PHONY: install
install:
	$(UV) sync --locked

## Install dependencies for Development (updates lock if needed)
.PHONY: dev
dev:
	$(UV) sync --all-extras

## Nuke uv.lock and fully resync (Deep Clean)
.PHONY: lock-refresh
lock-refresh:
	rm -f uv.lock
	$(UV) sync --all-extras
	@echo "Lockfile refreshed and dependencies installed."

## Delete all compiled Python files and temporary build artifacts
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".ruff_cache" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name "*.tmp*" -exec rm -rf {} \;

## Lint using ruff (check only)
.PHONY: lint
lint:
	ruff format --check
	ruff check

## Format source code with ruff (fix violations)
.PHONY: format
format:
	ruff check --fix
	ruff format

## Run tests
.PHONY: test
test:
	python -m pytest tests

#################################################################################
# DAGSTER COMMANDS                                                              #
#################################################################################

## Start Dagster dev server (Docker Entrypoint)
.PHONY: dagster-start
dagster-start:
	dagster dev -h 0.0.0.0 -p 3000

## Stop Dagster dev server
.PHONY: dagster-stop
dagster-stop:
	pkill -f "dagster dev" || echo "Dagster not running"

## Restart Dagster dev server
.PHONY: dagster-restart
dagster-restart: dagster-stop dagster-start

#################################################################################
# DOCUMENTATION                                                                 #
#################################################################################

## Serve MkDocs documentation (accessible on port 8000)
.PHONY: docs
docs:
	mkdocs serve -f /workspace/docs/mkdocs.yml -a 0.0.0.0:8000

#################################################################################
# Self Documenting Commands                                                     #
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
	@$(PYTHON_INTERPRETER) -c "${PRINT_HELP_PYSCRIPT}" < $(MAKEFILE_LIST)