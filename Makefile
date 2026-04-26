.PHONY: help be fe dev install dev-stop

SHELL := /bin/bash
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
FRONTEND_PORT ?= 5173

help:
	@echo "Available targets:"
	@echo "  make be          - Run backend only (FastAPI server with auto-reload)"
	@echo "  make fe          - Run frontend only (Vite dev server)"
	@echo "  make dev         - Run both backend and frontend concurrently"
	@echo "  make dev-stop    - Stop any lingering background processes"
	@echo "  make install     - Install dependencies for both BE and FE"
	@echo ""
	@echo "Environment variables:"
	@echo "  BACKEND_HOST     - Backend host (default: 127.0.0.1)"
	@echo "  BACKEND_PORT     - Backend port (default: 8000)"
	@echo "  FRONTEND_PORT    - Frontend port (default: 5173)"
	@echo ""
	@echo "Example usage:"
	@echo "  make install     # First time: install dependencies"
	@echo "  make dev         # Run both backend and frontend"

# Run backend only (with uv venv activated)
be:
	@. "$$(uv venv)" && uv run zipmould viz serve --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload

# Run frontend only
fe:
	@cd viz-web && bun run dev -- --port $(FRONTEND_PORT)

# Run both backend and frontend concurrently
dev:
	@echo "Starting backend on http://$(BACKEND_HOST):$(BACKEND_PORT)"
	@echo "Starting frontend on http://localhost:$(FRONTEND_PORT)"
	@echo "Press Ctrl+C to stop both services"
	@echo ""
	@(. "$$(uv venv)" && uv run zipmould viz serve --host $(BACKEND_HOST) --port $(BACKEND_PORT) --reload) & \
	(cd viz-web && bun run dev -- --port $(FRONTEND_PORT)) & \
	wait

# Stop any lingering background processes
dev-stop:
	@pkill -f "uvicorn" || true
	@pkill -f "vite" || true
	@echo "Stopped backend and frontend processes"

# Install dependencies for both backend and frontend
install:
	@echo "Installing backend dependencies..."
	uv sync
	@echo "Installing frontend dependencies..."
	cd viz-web && bun install
	@echo "✓ Setup complete!"
	@echo ""
	@echo "Run 'make dev' to start both backend and frontend"
