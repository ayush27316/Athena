#!/usr/bin/env bash

set -e
set -x

# Start the FastAPI development server
uv run fastapi dev app/main.py
