MAP ?= 01_linear_path.txt

.PHONY: install run debug clean lint lint-strict

install:
	python3 -m pip install flake8 mypy

run:
	python3 main.py $(MAP)

debug:
	python3 -m pdb main.py $(MAP)

clean:
	rm -rf __pycache__ .mypy_cache

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
