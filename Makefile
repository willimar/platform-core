# Makefile — platform-core / agent-sdk

.PHONY: help install test lint format check run clean

# ── Setup ──────────────────────────────────────────────────────

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências (runtime + dev)
	uv sync --group dev

# ── Qualidade ──────────────────────────────────────────────────

test: ## Roda testes com coverage
	uv run pytest --cov --cov-report=term-missing

lint: ## Verifica lint sem corrigir
	uv run ruff check src/ tests/

format: ## Formata código
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

check: lint test ## Lint + testes (CI local)

# ── Execução ───────────────────────────────────────────────────

run: ## Executa exemplo local
	uv run platform run ../google-calendar-agent/agent.yaml --verbose

# ── Limpeza ────────────────────────────────────────────────────

clean: ## Remove artefatos de build e cache
	rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +