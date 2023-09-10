SHELL=/bin/bash

.PHONY: lint
lint:
	python -m flake8 screen_brightness_control --max-line-length 119 --ignore W503

.PHONY: testquick
testquick:
	python tests/testall.py --synthetic

.PHONY: test
test: lint
	make testquick

.PHONY: testall
testall:
	python tests/testall.py

.PHONY: mypy
mypy:
	python -m mypy screen_brightness_control

.PHONY: docs
docs:
	cd docs/docs && git reset --hard
	python docs/make.py
