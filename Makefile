PYTHON ?= python

all: package

doc:
	@sphinx-apidoc -o ./docs/source/ ./ktt/
	@make -C docs html

package: clean
	@versioneer install
	@$(PYTHON) setup.py bdist_wheel

clean:
	@rm -rf build/ dist/

.PHONY: all package clean doc
