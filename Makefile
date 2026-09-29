PYTHON ?= python3

.PHONY: run test clean

run:
	$(PYTHON) src/main.py

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

clean:
	rm -rf build
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
