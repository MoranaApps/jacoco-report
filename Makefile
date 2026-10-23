# Standard commands, the same for people and agents. Each target wraps a real project command.
# Usage: make <target>. One test file or test: make test T=<path>

.PHONY: help setup run build test lint format check

help: ## List the targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup: ## Install dependencies
	pip install -r requirements.txt

run: ## Start the action locally (needs INPUT_* and GITHUB_* env vars, see DEVELOPER.md)
	python3 main.py

build: ## Sanity-compile every source file (no packaged artifact: this ships as Python source)
	python3 -m py_compile $$(git ls-files '*.py')

test: ## Run unit + offline integration tests, or one file/test with T=<path>
	pytest --cov=. $(if $(T),$(T),tests/ --ignore=tests/integration/live) --cov-fail-under=80

lint: ## Lint and type-check
	pylint $$(git ls-files '*.py')
	mypy .

format: ## Format the code
	black $$(git ls-files '*.py')

check: lint test build ## Everything that must pass before work is done
	black --check $$(git ls-files '*.py')
