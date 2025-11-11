#################################################################################
# GLOBALS                                                                       #
#################################################################################

PROJECT_NAME = leafletslm
PYTHON_VERSION = 3.12
PYTHON_INTERPRETER = python

#################################################################################
# COMMANDS                                                                      #
#################################################################################


## Install Python dependencies
.PHONY: requirements
requirements:
	uv sync

.PHONY: dev
requirements:
	uv sync --all-extras

## Delete all compiled Python files
.PHONY: clean
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.tmp*" -exec rm -rf {} \;


.PHONY: prune
prune:
	rm -rf .venv


## Lint using ruff (use `make format` to do formatting)
.PHONY: lint
lint:
	ruff format --check
	ruff check

## Format source code with ruff
.PHONY: format
format:
	ruff check --fix
	ruff format



## Run tests
.PHONY: test
test:
	python -m pytest tests


## Set up Python interpreter environment
.PHONY: create_environment
create_environment:
	uv venv --python $(PYTHON_VERSION)
	@echo ">>> New uv virtual environment created. Activate with:"
	@echo ">>> Windows: .\\\\.venv\\\\Scripts\\\\activate"
	@echo ">>> Unix/macOS: source ./.venv/bin/activate"
	



#################################################################################
# PROJECT RULES                                                                 #
#################################################################################


## Make dataset
.PHONY: data
data: requirements
	$(PYTHON_INTERPRETER) leaflets/dataset.py


#################################################################################
# DAGSTER COMMANDS                                                              #
#################################################################################

## Start Dagster dev server (inside container)
.PHONY: dagster-up
dagster-up:
	/workspace/scripts/start-dagster.sh

## Stop Dagster dev server
.PHONY: dagster-down
dagster-down:
	pkill -f "dagster dev" || echo "Dagster not running"

## Restart Dagster dev server
.PHONY: dagster-restart
dagster-restart: dagster-stop dagster-dev

## Clean Dagster storage (runs, schedules, etc)
.PHONY: dagster-clean
dagster-clean:
	rm -rf .dagster/storage/*
	mkdir -p .dagster/storage
	@echo ">>> Dagster storage cleaned"



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
