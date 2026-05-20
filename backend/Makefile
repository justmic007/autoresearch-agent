.PHONY: help setup env infra infra-down install run test lint benchmark logs clean

# ── colours ──────────────────────────────────────────────────────────────────
BOLD  := \033[1m
GREEN := \033[32m
CYAN  := \033[36m
RESET := \033[0m

help: ## Show all available commands
	@echo ""
	@echo "$(BOLD)AutoResearch Agent — available commands$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ \
		{ printf "  $(CYAN)make %-15s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ── first-time setup ─────────────────────────────────────────────────────────

setup: env install infra ## Full first-time setup (env + deps + infrastructure)
	@echo "$(GREEN)✓ Setup complete. Fill in your API keys in .env then run: make run$(RESET)"

env: ## Copy .env.example to .env (skip if .env already exists)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created — open it and fill in your API keys$(RESET)"; \
	else \
		echo "  .env already exists, skipping"; \
	fi

install: ## Install Python dependencies into the active virtualenv
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(RESET)"

# ── infrastructure ────────────────────────────────────────────────────────────

infra: ## Start Redis + ChromaDB (infrastructure only, no app)
	@echo "Starting Redis and ChromaDB..."
	docker compose up -d redis chromadb
	@echo "$(GREEN)✓ Infrastructure started$(RESET)"
	@echo "  Waiting for health checks..."
	@sleep 5
	docker compose ps

infra-down: ## Stop infrastructure containers
	docker compose down
	@echo "$(GREEN)✓ Infrastructure stopped$(RESET)"

# ── running the app ───────────────────────────────────────────────────────────

run: ## Start the full stack (app + Redis + ChromaDB) via Docker
	docker compose up --build

dev: ## Run the API locally with hot-reload (infrastructure must be running)
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

query-pretty: ## Send a query and print formatted report (usage: make query-pretty Q="your question")
	@curl -s -X POST http://localhost:8000/research \
		-H "Content-Type: application/json" \
		-d '{"query": "$(Q)"}' | python app/utils/printer.py

# ── testing ───────────────────────────────────────────────────────────────────

test: ## Run unit tests
	pytest tests/ -v

lint: ## Run linter (ruff)
	ruff check app/ tests/

# ── agent testing ─────────────────────────────────────────────────────────────

test-planner: ## Smoke test: run Planner agent only
	@python -c "\
from app.graph.state import initial_state; \
from app.agents import planner; \
s = initial_state('What is quantum computing?', 'smoke-1'); \
r = planner.run(s); \
print('Subtasks:', r['subtasks']); \
print('Latency:', r['metrics'][0]['latency_ms'], 'ms')"

test-pipeline: ## Smoke test: run full Planner → Search pipeline
	@python -c "\
from app.graph.state import initial_state; \
from app.agents import planner, search; \
s = initial_state('AI regulation in the EU', 'smoke-2'); \
s = planner.run(s); \
s = search.run(s); \
print('Subtasks:', s['subtasks']); \
print('Search result sets:', len(s['search_results']))"

test-full: ## Run the complete agent pipeline end-to-end
	@python -c "\
from app.graph.workflow import run_research; \
result = run_research('What is the state of nuclear fusion in 2025?', 'demo-1'); \
print(result['report'][:600]); \
print(); \
print('Quality:', result['quality_score']['total'], '/ 30'); \
print('Duration:', round(result['finished_at'] - result['started_at'], 1), 's')"

# ── evaluation ────────────────────────────────────────────────────────────────

benchmark: ## Run the 5-query benchmark and print metrics table
	python -m app.eval.benchmark

# ── api testing ───────────────────────────────────────────────────────────────

query: ## Send a test query to the running API (usage: make query Q="your question")
	@curl -s -X POST http://localhost:8000/research \
		-H "Content-Type: application/json" \
		-d '{"query": "$(Q)"}' | python -m json.tool

health: ## Check API health endpoint
	@curl -s http://localhost:8000/health | python -m json.tool

# ── logs & monitoring ─────────────────────────────────────────────────────────

logs: ## Tail logs from all running containers
	docker compose logs -f

logs-app: ## Tail app container logs only
	docker compose logs -f app

# ── cleanup ───────────────────────────────────────────────────────────────────

clean: ## Stop containers and remove volumes (WARNING: deletes ChromaDB + Redis data)
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned up$(RESET)"