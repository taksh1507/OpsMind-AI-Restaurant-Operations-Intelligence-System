"""Pytest Configuration - Global Fixtures and Setup"""

import sys
from pathlib import Path

# Add the project root to the Python path
# This allows pytest to find the 'app' module from any working directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
