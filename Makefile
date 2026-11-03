.PHONY: run test lint format build-kb install eval

run:
	streamlit run app.py

test:
	python -m pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .

build-kb:
	python scripts/build_kb.py

install:
	pip install -e ".[dev]"

eval:
	python scripts/eval_agent.py
