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

.PHONY: docs
docs:
	cd docs/docs && git reset --hard
	python -m pip install -r requirements-dev.txt
	python docs/make.py

.PHONY: release
release: docs
	if [ ! -z "`git diff`" ]; then echo "Git diff is not empty. Commit changes before releasing" && exit 1; fi
	python -m pip install --upgrade build
	python -m build -w

.PHONY: publish
publish: release
	$(eval version=$(shell grep '^__version__' screen_brightness_control/_version.py | cut -d"'" -f2))
	@echo Git tag and push tags
	git tag v$(version)
	git push --tags
	@echo Upload to PyPI
	python -m pip install --upgrade twine
	twine upload dist/*$(version).tar.gz dist/*$(version)*.whl
	@echo Stage updated documentation with git
	cd docs/docs && find . -maxdepth 2 -type f -not -path '*/[@.]*' | while read file; do git add "$$file"; done
	cd docs/docs && git add docs/$(version)/*
	@echo Commit and push new docs
	cd docs/docs && git commit -m "Bump v$(version)" && git push origin gh-pages
