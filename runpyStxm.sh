#!/bin/bash

set -e

# Resolve relative application paths from this checkout, not the caller's directory.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd -- "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Function to find the conda command
find_conda() {
    # The desktop installer supplies Conda explicitly because KDE may not
    # inherit the PATH configured by an interactive shell.
    if [[ -n "${CONDA_EXE:-}" && -x "$CONDA_EXE" ]]; then
        echo "$CONDA_EXE"
    elif command -v conda &> /dev/null; then
        echo "$(command -v conda)"
    else
        echo "Conda command not found. Please ensure conda is installed and in your PATH." >&2
        return 1
    fi
}

# Find the conda command
CONDA_CMD=$(find_conda)

# Initialize conda
CONDA_HOOK=$("$CONDA_CMD" shell.bash hook)
eval "$CONDA_HOOK"

# Activate the conda environment
conda activate pyStxm

# Load the beamline settings and launch the application.
source ./reqd_env_vars.sh
exec python ./cls/applications/pyStxm/runPyStxm.py
