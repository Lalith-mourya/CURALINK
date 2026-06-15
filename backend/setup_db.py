"""
Standalone script to initialise the SQLite database.

Usage:
    python setup_db.py
"""

import sys
import os

# Ensure the backend directory is on the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import init_db


def main():
    print("Setting up the database …")
    init_db()
    print("Database setup complete ✅")


if __name__ == '__main__':
    main()
