PYTHON ?= python
VERSION=

all: package

doc:
	@sphinx-apidoc -o ./docs/source/ ./ktt/
	@make -C docs html singlehtml

package: clean doc
	@git tag $(VERSION)
	@versioneer install
	@$(PYTHON) setup.py bdist_wheel
	@cp -r docs/build/singlehtml/ dist/doc
	@tar czf ktt_$(VERSION).tar.gz dist/

clean:
	@rm -rf build/ dist/

.PHONY: all package clean doc
