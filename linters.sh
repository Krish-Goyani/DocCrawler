#!/bin/bash
# Delete all __pycache__ directories excluding dhiwise_3_0_ragenv
find . -type d \( -name "__pycache__" -a ! -path "./env/*" \) -prune -exec rm -r {} +
# Run autoflake to remove unused imports in Python files excluding dhiwise_3_0_ragenv
find . -type f -name "*.py" -not -path "./env/*" -exec autoflake --remove-all-unused-imports --in-place {} \;
# Run isort to sort imports in Python files excluding dhiwise_3_0_ragenv
find . -type f -name "*.py" -not -path "./env/*" -exec isort {} \;
# Run black to format Python files with a line length of 120 characters excluding dhiwise_3_0_ragenv
find . -type f -name "*.py" -not -path "./env/*" -exec black {} --line-length 80 \;
# Run vulture to find unused functions in Python files excluding dhiwise_3_0_ragenv
vulture . --exclude env