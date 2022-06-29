SHELL=/bin/bash

.PHONY: test
test:
	python tests/testall.py --synthetic

.PHONY: testall
testall:
	python tests/testall.py

.PHONY: docs
docs:
	python -m pip install -r docs/requirements.txt
	python docs/make.py

.PHONY: release
release: docs
	python -m pip install --upgrade build
	python -m build

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
