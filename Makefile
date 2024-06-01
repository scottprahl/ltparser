SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs
BUILDDIR      = docs/_build

lint:
	-ruff check .

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	open docs/_build/index.html

clean:
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf docs/.ipynb_checkpoints
	rm -rf docs/_build
	rm -rf docs/api
	rm -rf ltparser/__pycache__
	rm -rf tests/__pycache__

notecheck:
	make clean
	pytest --verbose test_all_notebooks.py
	rm -rf __pycache__

rcheck:
	make clean
	make lint
	make test
	make notecheck
	touch docs/*ipynb
	touch docs/*rst
	make html
	check-manifest
	pyroma -d .
	tox

test:
	pytest tests/tests.py

.PHONY: clean lint rcheck html
