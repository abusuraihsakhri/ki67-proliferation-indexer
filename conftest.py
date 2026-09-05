"""
Pytest configuration for Ki67 Proliferation Indexer.

Sets required environment variables before any module-level imports occur.
"""
import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set a deterministic test-only audit key (never used in production)
os.environ.setdefault("AUDIT_SECRET_KEY", "ki67-test-only-secret-key-not-for-production-use")
