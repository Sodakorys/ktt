PYTHON ?= python

all: package

doc:
	@sphinx-apidoc -o ./docs/source/ ./ktt/
	@make -C docs html singlehtml

package: clean doc
	@versioneer install
	@$(PYTHON) setup.py bdist_wheel
	@cp -r docs/build/singlehtml/ dist/doc

clean:
	@rm -rf build/ dist/

.PHONY: all package clean doc
