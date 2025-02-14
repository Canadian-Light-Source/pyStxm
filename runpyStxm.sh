#!/bin/bash

# Function to find the conda command
find_conda() {
    if command -v conda &> /dev/null; then
        echo "$(command -v conda)"
    else
        echo "Conda command not found. Please ensure conda is installed and in your PATH."
        exit 1
    fi
}

# Find the conda command
CONDA_CMD=$(find_conda)

# Initialize conda
eval "$($CONDA_CMD shell.bash hook)" &> /dev/null

# Activate the conda environment
conda activate pyStxm310 &> /dev/null

# Activate the conda environment
#source /home/bergr/pyStxm/miniconda/bin/activate pyStxm310 

source ./reqd_env_vars.sh
python ./cls/applications/pyStxm/runPyStxm.py

