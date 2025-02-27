# File: Makefile

# purpose:
#	build resources in pyStxm documentation

PYTHON = python3
SPHINX = sphinx-build
BUILD_DIR = build

.PHONY: help install clean html all local

help ::
	@echo ""
	@echo "NeXus: Testing the Wiki files and building the documentation:"
	@echo ""

	@echo "make install            Install all requirements to run tests and builds."
	@echo "make clean              Remove all build files."
	@echo "make html               Build HTML version of manual. Requires prepare first."
	@echo "make all                Builds complete web site for the wiki (in build directory)."
	@echo ""
	@echo "Note:  All builds of the wiki will occur in the 'build/' directory."
	@echo "   For a complete build, run 'make all' in the root directory."
	@echo "   Developers of the NeXus wiki can use 'make local' to"
	@echo "   confirm the documentation builds."
	@echo ""

install ::
	$(PYTHON) -m pip install -r ./sphinx/requirements.txt

clean ::
	$(RM) -rf ./sphinx/$(BUILD_DIR)

html:
	$(SPHINX) -b html -W ./sphinx/ ./sphinx/$(BUILD_DIR)/html

# for developer's use on local build host
local ::
#	$(MAKE) prepare
	$(MAKE) html

all ::
	$(MAKE) clean
	$(MAKE) html
	@echo "HTML built: `ls -lAFgh ./sphinx/build/html/index.html`"

