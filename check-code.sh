#!/usr/bin/env bash

set -eu

# Install pre-commit if needed. People always forget to do this.
if ! command -v pre-commit &> /dev/null
then
    echo "pre-commit could not be found"
    echo "Installing pre-commit..."

    if ! pip install pre-commit; then
        echo "Failed to install pre-commit. Please check your Python and pip installation."
        exit 1
    fi
fi
pre-commit install > /dev/null

# We still want to run tests if this fails
# (it's lower priority and may just be fixing formatting.)
pre-commit run -a || true

echo "Running pytest..."
python -m pytest || { echo "Pytest failed. Fix the issues and re-run the script."; exit 1; }
