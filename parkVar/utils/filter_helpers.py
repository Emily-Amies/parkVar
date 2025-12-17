"""
Filtering utilities for annotated variant data.

This module handles:
- reading the annotated CSV
- filtering rows by Patient_ID based on form selections
- rendering the filtered results alongside checkbox controls

Author: Emily Amies
Group: 4

Notes:
- Expects an annotated CSV from the annotation stage.
- Integrates with Flask templates defined in flask_utils.
"""


import pandas as pd
from flask import render_template_string, request

from parkVar.utils import flask_utils
from parkVar.utils.logger_config import logger


def _read_anno_data(anno_path):
    """
    Load annotated variant data from a CSV.

    Parameters
    ----------
    anno_path : pathlib.Path
        Path to the annotated CSV file.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing annotated data.

    Raises
    ------
    flask_utils.CSVReadError
        If the CSV cannot be read.
    """

    # Create pandas dataframe from csv
    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        raise flask_utils.CSVReadError(
            context="anno_data.csv", original_exception=e
        )

    return df


def _filter_df(df, filtered_path):
    """
    Filter a DataFrame by selected Patient_ID values from a Flask form.

    Parameters
    ----------
    df : pandas.DataFrame
        The pre-annotated dataframe.
    filtered_path : pathlib.Path
        Path where the filtered CSV should be written.

    Returns
    -------
    pandas.DataFrame
        The filtered dataframe.
    list[str]
        Patient IDs selected by the user.
    str
        Text describing the applied filter (for display).

    Raises
    ------
    flask_utils.MissingColumnError
        If the Patient_ID column is missing.
    """

    # Check if Patient_ID is in dataframe
    if "Patient_ID" not in df.columns:
        raise flask_utils.MissingColumnError(
            context="Patient_ID", original_exception=KeyError("Patient_ID")
        )

    # List of selected patient IDs from the form
    selected_ids = request.form.getlist("patient_id")

    # Apply filter
    if selected_ids:
        filtered_df = df[df["Patient_ID"].astype(str).isin(selected_ids)]
        logger.info(f"Filter applied to Patient_ID(s): {selected_ids}")
        applied_text = f"Filtered by: {', '.join(selected_ids)}"
    else:
        # No boxes ticked = show everything
        filtered_df = df.copy()
        logger.info("No filter applied (no Patient_ID selected)")
        applied_text = "No filter selected. Showing all rows."

    # Write filtered data to CSV
    filtered_df.to_csv(filtered_path, index=False)

    return filtered_df, selected_ids, applied_text


def _show_filter_page(df, filtered_df, selected_ids, applied_text):
    """
    Render a filter results page showing checkboxes and the filtered table.

    Parameters
    ----------
    df : pandas.DataFrame
        The full annotated DataFrame.
    filtered_df : pandas.DataFrame
        The filtered DataFrame.
    selected_ids : list[str]
        List of selected Patient_ID values.
    applied_text : str
        Text describing the applied filter.

    Returns
    -------
    str
        Rendered HTML containing the checkbox form and filtered table.
    """

    # Rebuild checkbox values so the page can re-render them
    patient_ids = sorted(
        df["Patient_ID"].astype(str).dropna().unique().tolist()
    )

    # Build the table HTML for the filtered frame
    table_html = flask_utils.create_table(filtered_df)

    return render_template_string(
        flask_utils.ANNO_TEMPLATE,
        applied_text=applied_text,
        table=table_html,
        patient_ids=patient_ids,
        selected_ids=selected_ids,
    )
