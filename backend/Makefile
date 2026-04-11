# Makefile for Agentic Crawler
# Note: On Windows, use these commands directly or install make via chocolatey

.PHONY: help install install-dev run test clean format lint

help:
	@echo "Available commands:"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make run          - Run the application"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make format       - Format code with black"
	@echo "  make lint         - Lint code with ruff"
	@echo "  make clean        - Clean up generated files"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

run:
	python main.py

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=src/agentic_crawler --cov-report=html --cov-report=term

format:
	black src/ tests/

lint:
	ruff check src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .coverage htmlcov/
