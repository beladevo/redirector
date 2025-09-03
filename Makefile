# Makefile for Redirector development and deployment

.PHONY: help install dev test lint format typecheck clean build docker run docker-dev docs

# Default target
help:
	@echo "🎯 Redirector - Professional URL Redirector"
	@echo ""
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  dev         Install development dependencies"
	@echo "  test        Run tests"
	@echo "  lint        Run linting (ruff)"
	@echo "  format      Format code (black + ruff)"
	@echo "  typecheck   Run type checking (mypy)"
	@echo "  clean       Clean build artifacts"
	@echo "  build       Build package"
	@echo "  docker      Build Docker image"
	@echo "  run         Run development server"
	@echo "  docker-dev  Run with Docker Compose"
	@echo "  docs        Generate documentation"

# Installation
install:
	pip install -r requirements.txt

dev: install
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest tests/ -v --cov=src/redirector --cov-report=html

test-integration:
	pytest tests/integration/ -v -m integration

# Code quality
lint:
	ruff check src/ tests/
	
format:
	black src/ tests/
	ruff check --fix src/ tests/

typecheck:
	mypy src/redirector/

# Quality check all
check: lint typecheck test

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Building
build: clean
	python -m build

# Docker
docker:
	docker build -t redirector:latest .

docker-dev:
	docker-compose up --build

docker-tunnel:
	docker-compose --profile tunnel up --build

docker-prod:
	docker-compose --profile production up --build -d

# Development server
run:
	python -m redirector.cli.main run --redirect https://example.com --campaign dev-test

run-demo:
	python -m redirector.cli.main run \
		--redirect https://example.com \
		--campaign demo-campaign \
		--dashboard-auth admin:secret123 \
		--tunnel

# Configuration
config:
	python -m redirector.cli.main config --output redirector-config.yaml

# Statistics
stats:
	python -m redirector.cli.main stats --campaign demo-campaign

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@echo "See README.md for complete documentation"

# Pre-commit hooks
pre-commit:
	pre-commit run --all-files

# Install system dependencies (Ubuntu/Debian)
install-deps:
	sudo apt-get update
	sudo apt-get install -y python3-dev build-essential curl

# Setup development environment
setup: install-deps dev
	@echo "✅ Development environment ready!"
	@echo "Run 'make run' to start the development server"

# Performance testing
load-test:
	@echo "🔧 Load testing requires additional tools"
	@echo "Install: pip install locust"
	@echo "Run: locust -f tests/load/locustfile.py --host http://localhost:8080"

# Security audit
security:
	pip-audit

# Release preparation
release-check: check security
	@echo "✅ Release checks passed"

# Database operations
db-reset:
	rm -f logs.db
	@echo "🗑️ Database reset"

db-backup:
	cp logs.db logs_backup_$(shell date +%Y%m%d_%H%M%S).db
	@echo "💾 Database backed up"