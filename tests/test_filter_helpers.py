"""
Tests for filter_helpers.

Author: Emily Amies
Group: 4

Covers:
- reading annotated CSV into a DataFrame
- filtering by Patient_ID with and without selections
- rendering the filter page with checkboxes and table output
"""

import pytest
import pandas as pd
from flask import Flask

from parkVar.utils import filter_helpers as filters
from parkVar.utils import flask_utils


class TestReadAnnoData:
    """Tests for _read_anno_data"""

    def test_read_anno_data_returns_dataframe_on_valid_csv(self, tmp_path):
        """_read_anno_data returns a DataFrame when given a valid CSV."""

        # Create dummy CSV file
        anno_path = tmp_path / "anno_data.csv"
        csv_content = "col1,col2\n1,2\n3,4\n"
        anno_path.write_text(csv_content, encoding="utf-8")

        # Create a dataframe using the function
        df = filters._read_anno_data(anno_path)

        # Check dataframe is correct
        assert list(df.columns) == ["col1", "col2"]
        assert len(df) == 2
        assert df.iloc[0]["col1"] == 1
        assert df.iloc[0]["col2"] == 2

    def test_read_anno_data_raises_csvreaderror_on_bad_input(self, tmp_path):
        """_read_anno_data raises CSVReadError for an invalid CSV file."""

        # Create an invalid CSV file
        anno_path = tmp_path / "anno_data.csv"
        anno_path.write_bytes(b"\x00\xff\x00\xff not csv")

        # _read_anno_data should raise an error
        with pytest.raises(flask_utils.CSVReadError) as excinfo:
            filters._read_anno_data(anno_path)

        # Check error message
        assert "anno_data.csv" in str(excinfo.value)


@pytest.fixture
def app_filter():
    """Flask app fixture providing context for request/flash handling."""
    app = Flask(__name__)
    app.secret_key = "testing"  # required for flash()
    return app


class TestFilterDf:
    """Tests for _filter_df"""

    def test_filter_df_raises_missingcolumnerror(self, tmp_path, app_filter):
        """_filter_df raises MissingColumnError if Patient_ID column is 
        missing."""
        # Create dummy pandas dataframe
        df = pd.DataFrame({"X": [1, 2]})
        filtered_path = tmp_path / "filtered.csv"

        # Patient ID column missing so will raise MissingColumnError
        with app_filter.test_request_context("/fake", method="POST", data={}):
            with pytest.raises(flask_utils.MissingColumnError) as excinfo:
                filters._filter_df(df, filtered_path)

        # Check error message
        assert "Patient_ID" in str(excinfo.value)

    def test_filter_df_filters_selected_ids(self, tmp_path, app_filter):
        """_filter_df returns only rows matching selected Patient_ID 
        values."""
        # Create dummy pandas dataframe
        df = pd.DataFrame(
            {"Patient_ID": ["A", "B", "C"], "Value": [10, 20, 30]}
        )

        filtered_path = tmp_path / "filtered.csv"

        form_data = {"patient_id": ["B", "C"]}  # ChatGPT

        with app_filter.test_request_context(
            "/fake", method="POST", data=form_data
        ):
            filtered_df, selected_ids, applied_text = filters._filter_df(
                df, filtered_path
            )

        # Check filtered_df
        assert list(filtered_df["Patient_ID"]) == ["B", "C"]

        # Check the selected IDs
        assert selected_ids == ["B", "C"]

        # Checkl the text output
        assert applied_text == "Filtered by: B, C"

    def test_filter_df_no_selected_ids_returns_full_df(
        self, tmp_path, app_filter
    ):
        """_filter_df returns full DataFrame and message when no IDs 
        selected."""
        # Create dummy pandas dataframe
        df = pd.DataFrame(
            {"Patient_ID": ["A", "B", "C"], "Value": [10, 20, 30]}
        )

        filtered_path = tmp_path / "filtered.csv"

        with app_filter.test_request_context("/fake", method="POST", data={}):
            filtered_df, selected_ids, applied_text = filters._filter_df(
                df, filtered_path
            )

        # Check the whole dataframe is returned
        assert len(filtered_df) == 3

        # This should be empty
        assert selected_ids == []

        # Check text is correct
        assert applied_text == "No filter selected. Showing all rows."


class TestShowFilterPage:
    """Tests for _show_filter_page"""

    def test_show_filter_page_renders_page(self, app_filter):
        """_show_filter_page returns HTML containing table and Patient_ID 
        checkboxes."""
        # Create dummy pandas dataframe
        df = pd.DataFrame(
            {"Patient_ID": ["3", "1", "2"], "Value": [10, 20, 30]}
        )

        # Mock outputs from previous function
        filtered_df = df[df["Patient_ID"].isin(["1", "2"])]
        selected_ids = ["1", "2"]
        applied_text = "Filtered by: 1, 2"

        # Create HTML string using funtion
        with app_filter.test_request_context("/fake"):
            html = filters._show_filter_page(
                df, filtered_df, selected_ids, applied_text
            )

        # Check the HTML string was returned
        assert isinstance(html, str)
        assert html.strip() != ""

        # Check it includes table content from filtered_df
        assert "1" in html
        assert "2" in html
        assert "Filtered by: 1, 2" in html

        # Patient_ids should be sorted
        # Page should contain checkboxes or elements referencing all ids
        assert "1" in html
        assert "2" in html
        assert "3" in html
