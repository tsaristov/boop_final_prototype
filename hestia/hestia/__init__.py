# Hestia Knowledge and Memory System
# This package contains the core components of the knowledge and memory system.

from .database import initialize_db

# Initialize the database when the package is imported
initialize_db()

# Version information
__version__ = "1.0.0"
__author__ = "Talos AI"
__description__ = "A simple, reliable knowledge and memory system for AI assistants"