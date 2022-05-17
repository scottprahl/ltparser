SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = docs
BUILDDIR      = docs/_build

pycheck:
	-pylint ltparser/ltparser.py
	-pylint ltparser/__init__.py

doccheck:
	-pydocstyle ltparser/ltparser.py
	-pydocstyle ltparser/__init__.py

html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	open docs/_build/index.html

clean:
	rm -rf dist
	rm -rf ltparser.egg-info
	rm -rf ltparser/__pycache__
	rm -rf docs/_build
	rm -rf docs/api
	rm -rf .tox
	rm -rf build
	rm -rf .pytest_cache
	rm -rf tests/__pycache__

notecheck:
	make clean
	pytest --verbose test_all_notebooks.py
	rm -rf __pycache__

rcheck:
	make clean
	make pycheck
	make doccheck
	make notecheck
	touch docs/*ipynb
	touch docs/*rst
	make html
	check-manifest
	pyroma -d .
	tox

test:
	tox

.PHONY: clean check rcheck html