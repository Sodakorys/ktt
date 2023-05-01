PYTHON ?= python

all: package


package: clean
	@versioneer install
	@$(PYTHON) setup.py bdist_wheel

clean:
	@rm -rf build/ dist/

.PHONY: all package clean
