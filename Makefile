#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = drugslm
PYTHON_VERSION = 3.12
PYTHON_INTERPRETER = python
UV = uv

#################################################################################
# DEPENDENCY MANAGEMENT                                                         #
#################################################################################

## Install dependencies strictly from lockfile (CI/Production). Fails if lock is outdated.
.PHONY: install
install:
	$(UV) sync --locked --all-extras

## Install or update dependencies even though lockfile is outdated.
.PHONY: update
update:
	$(UV) sync --all-extras

#################################################################################
# CODE QUALITY & TESTING                                                        #
#################################################################################

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
	$(PYTHON_INTERPRETER) -m pytest tests

## Delete all compiled Python files, build artifacts and caches
.PHONY: clean
clean:
	@echo ">>> Starting cleanup files, build artifacts and caches"
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	@echo ">>> Project cleanup complete"

#
#	# Dagster logs
#	find . -type d -name ".logs_queue" -exec rm -rf {} +
#	find . -type d -name ".nux" -exec rm -rf {} +
#

#################################################################################
# DAGSTER CONTROLLER                                                            #
#################################################################################

# Detect if the target is "dagster"
ifeq (dagster,$(firstword $(MAKECMDGOALS)))
  DAGSTER_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # Create dummy rule to not fail
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
		dagster dev -h 0.0.0.0 -p 3000; \
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
  # Create dummy rule to not fail
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
		echo "  down     Stop documentation server"; \
		echo "  restart  Restart the documentation server"; \
		echo "  build    Build static documentation to site/"; \
		echo "  deploy   Deploy documentation to GitHub Pages"; \
		echo ""; \
	elif [ "$(DOCS_ARGS)" = "up" ]; then \
		echo ">>> Serving documentation..."; \
		mkdocs serve -f docs/mkdocs.yml -a 0.0.0.0:8000; \
	elif [ "$(DOCS_ARGS)" = "down" ]; then \
		echo ">>> Stopping documentation server..."; \
		pkill -f "mkdocs serve" || echo "Mkdocs not running"; \
	elif [ "$(DOCS_ARGS)" = "restart" ]; then \
		$(MAKE) docs down; \
		$(MAKE) docs up; \
	elif [ "$(DOCS_ARGS)" = "build" ]; then \
		mkdocs build -f docs/mkdocs.yml; \
	elif [ "$(DOCS_ARGS)" = "deploy" ]; then \
		mkdocs gh-deploy -f docs/mkdocs.yml; \
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
	@$(PYTHON_INTERPRETER) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)
