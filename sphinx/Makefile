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
	$(PYTHON) -m pip install -r requirements.txt

clean ::
	$(RM) -rf $(BUILD_DIR)

html:
	$(SPHINX) -b html -W . $(BUILD_DIR)/html

all ::
	$(MAKE) clean
	$(MAKE) html
	@echo "HTML built: `ls -lAFgh build/html/index.html`"





# NeXus - Neutron and X-ray Common Data Format
#
# Copyright (C) 2008-2025 NeXus International Advisory Committee (NIAC)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# For further information, see http://www.nexusformat.org
