"""
Tests for refresh_session and related Flask routing behaviour.

Author: Emily Amies
Group: 4

Covers:
- deleting files from the temporary data directory
- redirecting back to the upload route after refresh
"""


import pytest
from flask import Flask, url_for

from parkVar.modules import flask_app



@pytest.fixture
def app():
    """Minimal Flask app with a dummy /upload route for testing redirects."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    @app.route("/upload")
    def upload():
        return "upload page"

    with app.app_context():
        yield app


def test_refresh_session_deletes_files_and_redirects(app, tmp_path):
    """refresh_session removes all files in the data directory and redirects 
    to /upload."""
    # Create some dummy files in a temporary directory
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("hello")
    f2.write_text("world")

    # Make sure they exist
    assert f1.exists()
    assert f2.exists()

    # Create an app context and check the response and location
    with app.test_request_context():
        response = flask_app.refresh_session(data_dir=tmp_path)
        expected_location = url_for("upload")

    assert list(tmp_path.iterdir()) == []

    assert response.status_code == 302
    assert response.headers["Location"] == expected_location
