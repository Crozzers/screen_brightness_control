SHELL=/bin/bash

.PHONY: lint
lint:
	python -m ruff check screen_brightness_control

.PHONY: format
format:
	python -m ruff check --select I --fix screen_brightness_control
	python -m ruff format screen_brightness_control
	python -m string_fixer -c . -t screen_brightness_control

.PHONY: testquick
testquick:
	python -m pytest

.PHONY: test
test: lint
	make testquick

.PHONY: testall
testall:
	python -m pytest

.PHONY: mypy
mypy:
	python -m mypy screen_brightness_control

.PHONY: docs
docs:
	cd docs/docs && git reset --hard
	python docs/make.py
