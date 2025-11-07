# File-Storm Makefile
# Convenience commands for development and deployment

.PHONY: help install setup run-web run-consumer run-producer test clean deploy

help:
	@echo "File-Storm Makefile Commands"
	@echo "============================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Complete setup (venv + deps + .env)"
	@echo ""
	@echo "Run Commands:"
	@echo "  make run-web      - Start Flask web server"
	@echo "  make run-consumer - Start consumer worker"
	@echo "  make run-producer - Start Selenium producer"
	@echo "  make run-all      - Start all services (tmux required)"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-init      - Initialize TimescaleDB schema"
	@echo "  make db-check     - Check database connection and counts"
	@echo ""
	@echo "Redis Commands:"
	@echo "  make redis-check  - Check Redis connection and stream"
	@echo "  make redis-clear  - Clear Redis stream (DANGEROUS)"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make test         - Run tests (if available)"
	@echo "  make clean        - Clean temporary files"
	@echo "  make deploy       - Deploy to Render"

install:
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt

setup:
	@echo "Running setup..."
	@chmod +x setup.sh
	@./setup.sh

run-web:
	@echo "Starting Flask web server..."
	python app.py

run-consumer:
	@echo "Starting consumer worker..."
	python consumer.py

run-producer:
	@echo "Starting Selenium producer..."
	python selenium_producer.py

run-all:
	@echo "Starting all services in tmux..."
	@tmux new-session -d -s filestorm 'python app.py'
	@tmux split-window -h 'python consumer.py'
	@tmux split-window -v 'python selenium_producer.py'
	@tmux attach-session -t filestorm

db-init:
	@echo "Initializing TimescaleDB schema..."
	@if [ -z "$$PG_URI" ]; then \
		echo "Error: PG_URI not set. Run: export PG_URI=your-connection-string"; \
		exit 1; \
	fi
	psql "$$PG_URI" -f schema.sql

db-check:
	@echo "Checking database..."
	@if [ -z "$$PG_URI" ]; then \
		echo "Error: PG_URI not set"; \
		exit 1; \
	fi
	@psql "$$PG_URI" -c "SELECT COUNT(*) as total_records FROM file_events;"

redis-check:
	@echo "Checking Redis stream..."
	@if [ -z "$$REDIS_URL" ]; then \
		echo "Error: REDIS_URL not set"; \
		exit 1; \
	fi
	@redis-cli -u "$$REDIS_URL" XLEN filestorm:uploads

redis-clear:
	@echo "⚠️  WARNING: This will delete all messages in the stream!"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		redis-cli -u "$$REDIS_URL" DEL filestorm:uploads; \
		echo "Stream cleared"; \
	fi

test:
	@echo "Running tests..."
	@echo "No tests configured yet"

clean:
	@echo "Cleaning temporary files..."
	rm -rf __pycache__
	rm -rf **/__pycache__
	rm -rf .pytest_cache
	rm -rf *.pyc
	rm -rf *.pyo
	rm -rf *.log
	rm -rf /tmp/filestorm_uploads/*
	rm -rf /tmp/filestorm_storage/*
	@echo "Cleaned!"

deploy:
	@echo "Deploying to Render..."
	@if ! command -v render &> /dev/null; then \
		echo "Render CLI not installed. Install with: npm install -g @render/cli"; \
		exit 1; \
	fi
	render deploy

