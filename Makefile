.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install db-up db-down db-reset dev-backend dev-worker dev-frontend \
        migrate migration lint format typecheck test test-backend test-frontend check

help: ## Show available commands
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Install backend, worker and frontend dependencies
	cd backend && uv sync
	cd worker && uv sync
	cd frontend && pnpm install

db-up: ## Start the local PostgreSQL container
	docker compose up -d postgres

db-down: ## Stop local dependencies
	docker compose down

db-reset: ## Destroy and recreate the local database volume
	docker compose down -v && docker compose up -d postgres

dev-backend: ## Run the API with reload
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run the worker placeholder
	cd worker && uv run python -m worker.main

dev-frontend: ## Run the Next.js dev server
	cd frontend && pnpm dev

migrate: ## Apply database migrations
	cd backend && uv run alembic upgrade head

migration: ## Create a migration: make migration m="add users"
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

lint: ## Lint backend, worker and frontend
	cd backend && uv run ruff check .
	cd worker && uv run ruff check .
	cd frontend && pnpm lint

format: ## Format backend, worker and frontend
	cd backend && uv run ruff format .
	cd worker && uv run ruff format .
	cd frontend && pnpm format

typecheck: ## Type-check backend, worker and frontend
	cd backend && uv run mypy app tests
	cd worker && uv run mypy worker tests
	cd frontend && pnpm typecheck

test-backend: ## Run backend and worker tests
	cd backend && uv run pytest
	cd worker && uv run pytest

test-frontend: ## Run frontend tests
	cd frontend && pnpm test

test: test-backend test-frontend ## Run all tests

check: lint typecheck test ## Run every check CI runs
