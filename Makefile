# Makefile to automate bot setup and run workflow

# Variables
PYTHON = python3
PIP = pip
VENV_DIR = venv

# Steps to set up the environment and install dependencies
setup: 
	@echo "Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Activating virtual environment..."
	. $(VENV_DIR)/bin/activate && \
	$(PIP) install -r requirements.txt
	@echo "Environment setup complete."

# Run the bot and web server
run:
	@echo "Starting bot and web server..."
	. $(VENV_DIR)/bin/activate && \
	python web_server.py

# Full setup and run process
start: setup run