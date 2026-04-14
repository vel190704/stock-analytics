.PHONY: help up down restart ps logs logs-all build shell init-db migrate seed seed-topics test lint format dashboard-dev

COMPOSE_FILE := docker/docker-compose.yml
BACKEND_SERVICE := backend

help: ## Show available targets
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Build and start infrastructure + backend
	docker compose -f $(COMPOSE_FILE) up -d --build
	@echo "API:         http://localhost:8000"
	@echo "Kafka UI:    http://localhost:8080"
	@echo "Prometheus:  http://localhost:9090"
	@echo "Grafana:     http://localhost:3000 (admin/admin)"

down: ## Stop all containers and remove volumes
	docker compose -f $(COMPOSE_FILE) down -v

restart: down up ## Full restart

ps: ## List compose services
	docker compose -f $(COMPOSE_FILE) ps

logs: ## Tail backend logs
	docker compose -f $(COMPOSE_FILE) logs -f $(BACKEND_SERVICE)

logs-all: ## Tail all logs
	docker compose -f $(COMPOSE_FILE) logs -f

build: ## Build images only
	docker compose -f $(COMPOSE_FILE) build

shell: ## Open shell in backend container
	docker compose -f $(COMPOSE_FILE) exec $(BACKEND_SERVICE) /bin/sh

init-db: ## Wait for postgres, ensure timescaledb, run alembic migrations
	docker compose -f $(COMPOSE_FILE) exec $(BACKEND_SERVICE) python scripts/init_db.py

migrate: init-db ## Alias for init-db

seed-topics: ## Create Kafka topics (no simulated market events)
	docker compose -f $(COMPOSE_FILE) exec $(BACKEND_SERVICE) python scripts/seed_topics.py --topics-only

seed: init-db seed-topics ## Initialize DB and Kafka topics
	@echo "Database and Kafka topics are ready."

test: ## Run backend tests
	pytest tests/ -v

lint: ## Run ruff and mypy
	ruff check src tests
	mypy src

format: ## Format Python code
	ruff check --fix src tests
	ruff format src tests

dashboard-dev: ## Start dashboard locally against backend
	cd dashboard && npm run dev
