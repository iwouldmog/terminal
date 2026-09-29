PYTHON ?= python3

.PHONY: run test demo clean

run:
	$(PYTHON) src/main.py $(ARGS)

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

demo:
	for script in scripts/test_*.sh; do sh "$$script"; done

clean:
	rm -rf build
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
