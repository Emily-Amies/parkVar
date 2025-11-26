import pandas as pd
import pytest
from flask import Flask
from parkVar.utils import flask_utils

# ChatGPT helped with HTML parts

# Create a flask app context - From ChatGPT
@pytest.fixture
def app():
    app = Flask(__name__)
    # Gives both app + request context
    with app.test_request_context('/'):
        yield app

class TestCreateTable:

    def test_create_table_renders_row_count_and_table(self, app):
        # Create a dummy dataframe
        df = pd.DataFrame(
            {'col1': [1, 2], 'col2': ['a', 'b']}
        )

        # Use function to create an html string
        html = flask_utils.create_table(df)

        # Check a string is created
        assert isinstance(html, str)

        # Check string for substrings like column names etc.
        assert '<p>Rows: 2</p>' in html
        assert '<table' in html
        
        # Column names
        assert 'col1' in html
        assert 'col2' in html

        # Values
        assert '1' in html
        assert 'b' in html

    def test_create_table_handles_empty_dataframe(self, app):
        # Create a dummy dataframe
        df = pd.DataFrame(columns=['col1', 'col2'])

        # Use function to change it into an html string
        html = flask_utils.create_table(df)

        # Still make strings but with 0 rows
        assert '<p>Rows: 0</p>' in html
        assert '<table' in html

        # Column names should still appear
        assert 'col1' in html
        assert 'col2' in html

class TestShowCheckboxes:

    def test_show_checkboxes_renders_patient_ids(self, app):
        # Create a dummy dataframe
        df = pd.DataFrame(
            {
                'Patient_ID': ['P1', 'P2', 'P3'],
                'col1': [1, 2, 3],
            }
        )

        # Create a dummy html table string
        table_html = '<table><tr><td>dummy</td></tr></table>'

        
        html = flask_utils.show_checkboxes(df, table_html)

        # Check the new html is a string
        assert isinstance(html, str)

        # Check the table is included
        assert 'dummy' in html

        # Check the Patient IDs are somewhere in the template
        assert 'P1' in html
        assert 'P2' in html
        assert 'P3' in html

    def test_show_checkboxes_marks_selected_ids(self, app):
        # Create a dummy dataframe
        df = pd.DataFrame(
            {
                'Patient_ID': ['P1', 'P2'],
                'col1': [1, 2],
            }
        )

        # Create a dummy html table string
        table_html = '<table><tr><td>dummy</td></tr></table>'

        # Select P2
        html = flask_utils.show_checkboxes(df, table_html, selected_ids=['P2'])

        # P2 is checked
        assert "P2" in html
        assert "checked" in html

    def test_show_checkboxes_raises_if_patient_id_missing(self, app):
        # Create a dummy dataframe
        df = pd.DataFrame(
            {
                'col1': [1, 2],
                'col2': [3, 4],
            }
        )

        # Create a dummy html table string
        table_html = '<table><tr><td>dummy</td></tr></table>'

        # Check if missing Patient_ID column raises error
        with pytest.raises(flask_utils.MissingColumnError) as excinfo:
            flask_utils.show_checkboxes(df, table_html)

        # Check if "Patient_ID" is in the error
        assert 'Patient_ID' in str(excinfo.value)