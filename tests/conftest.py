"""
tests/conftest.py — shared pytest fixtures.

Each test runs against a fresh in-memory SQLite database so tests never touch
the real bookclub.db and never depend on seed data.
"""

import pytest

from app import create_app
from extensions import db as _db


@pytest.fixture
def app():
    """A Flask app bound to an isolated in-memory database, with app context."""
    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
        }
    )
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    """The SQLAlchemy handle, scoped to the in-memory app above."""
    return _db
