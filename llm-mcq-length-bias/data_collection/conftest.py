"""Ensure the package directory is importable when running the tests from here
(the modules use top-level imports, mirroring the ``src/`` layout)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
