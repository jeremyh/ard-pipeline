#!/usr/bin/env python3
import runpy
from pathlib import Path

# Find script directory and locate _version.py
script_dir = Path(__file__).resolve().parent
version_path = script_dir.parent / "wagl" / "_version.py"

# Run the _version.py script and get its namespace
version_info = runpy.run_path(version_path)

print(version_info["__version__"])
