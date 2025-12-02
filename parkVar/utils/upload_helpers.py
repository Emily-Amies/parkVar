"""
Helpers for handling file upload, normalising input CSVs and persisting
uploaded data for the parkVar web interface.

This module provides:
- a wrapper for handling file uploads from a Flask request
- conversion of uploaded CSV files into pandas DataFrames
- tracking of files already uploaded in the current session
- writing combined input data to a CSV for downstream processing

Author: Emily Amies
Group: 4

Notes:
- Uploaded filenames are tracked in 'uploaded_files.txt' within the
  provided data directory.
- Input data are written/append to 'input_data.csv' in the same directory.
"""


from pathlib import Path
import io
import pandas as pd
from flask import Request, flash, render_template_string

from parkVar.utils import flask_utils
from parkVar.utils.logger_config import logger

def _upload_file(request):
    """
    Extract a file from a Flask request and perform basic validation.

    Parameters
    ----------
    request : flask.Request
        The incoming Flask request object.

    Returns
    -------
    werkzeug.datastructures.FileStorage or tuple
        The uploaded file object if present and valid.
        If no file is provided, returns a tuple:
        (rendered upload template HTML, 400).

    Notes
    -----
    The caller is responsible for handling the case where a tuple is
    returned instead of a file object.
    """

    # What happens when user uploads a file
    if request.method == "POST":
        # Flask object that holds the file, looks for input field named 'file'
        # from the HTML form
        file = request.files.get("file")

    # If no file is provided, sends a message and HTML status code 400
    # (bad request)
    if not file or file.filename == "":
        logger.warning("No file uploaded")
        flash("No file uploaded", "warning")
        return render_template_string(flask_utils.UPLOAD_TEMPLATE), 400
    else:
        logger.info(f"{file.filename} uploaded sucessfully")
        return file


def _create_pandas_dataframe(file):
    """
    Convert an uploaded CSV file into a pandas DataFrame and normalise columns.

    Steps
    -----
    - Decode the uploaded bytes as UTF-8.
    - Read into a DataFrame using pandas.
    - Set a Patient_ID column based on the filename (stem).
    - Drop any existing Patient_ID or ID columns to avoid duplication.

    Parameters
    ----------
    file : werkzeug.datastructures.FileStorage
        The uploaded file object.

    Returns
    -------
    pandas.DataFrame
        Normalised DataFrame containing the uploaded data.

    Raises
    ------
    flask_utils.CSVReadError
        If the file cannot be read into a DataFrame.
    """

    # Convert file object to a pandas dataframe
    try:
        text = file.read().decode("utf-8")
        # io.StringIO - pandas usually expects a file on disk. When a file is
        # read using a form, it is only raw bytes in memory. StringIO creates
        # an in-memory file-object that acts like a normal file
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise flask_utils.CSVReadError(
            context=file.filename, original_exception=e
        )

    # Add patient ID as first column
    patient_id = Path(file.filename).stem  # strips .csv
    if "Patient_ID" in df.columns:
        df = df.drop(columns=["Patient_ID"])
        logger.info("Patient_ID column exists. Deleting column.")
    df.insert(0, "Patient_ID", patient_id)

    # Remove ID column
    if "ID" in df.columns:
        df = df.drop(columns=["ID"])
        logger.info("ID column exists. Deleting column.")

    return df


def _check_existing_files(file, data_dir):
    """
    Track uploaded filenames and warn if a file has already been uploaded.

    Parameters
    ----------
    file : werkzeug.datastructures.FileStorage
        The uploaded file object.
    data_dir : pathlib.Path
        Directory where tracking and data files are stored.

    Returns
    -------
    str or None
        If the file has already been uploaded, returns rendered HTML for the
        annotation template (early exit case).
        Otherwise, updates the tracking file and returns None.

    Notes
    -----
    This function uses flash messaging to notify the user when a file has
    already been uploaded in the current session.
    """

    # File to store filenames that have been uploaded this session
    uploaded_files = Path(data_dir / "uploaded_files.txt")

    # Create a list from the file of uploaded filenames
    if not uploaded_files.exists():
        filenames = list()
    else:
        filenames = [
            line.strip()
            for line in uploaded_files.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    # Check the selected file against list of filenames already uploaded
    if file.filename in filenames:
        logger.warning(f"{file.filename} already uploaded")
        flash(f"⚠ {file.filename} has already been uploaded", "warning")
        return render_template_string(flask_utils.UPLOAD_ANNO_TEMPLATE)

    # Save the updated list of uploaded files
    filenames.append(file.filename)
    uploaded_files.write_text("\n".join(sorted(filenames)), encoding="utf-8")


def _write_to_csv(data_dir, file, df):
    """
    Append uploaded data to the combined input CSV, or create it if missing.

    Parameters
    ----------
    data_dir : pathlib.Path
        Directory where 'input_data.csv' is stored.
    file : werkzeug.datastructures.FileStorage
        The uploaded file object (used for logging and messaging).
    df : pandas.DataFrame
        DataFrame to write or append.

    Notes
    -----
    - If 'input_data.csv' exists, the new data are appended without a header.
    - If it does not exist, the file is created with a header row.
    """
    # CSV file to store the input data
    input_data_path = data_dir / "input_data.csv"

    # This will save the dataframe as a CSV in a temporary data file.
    # It will append the CSV to existing CSVs if present. This means the user
    # can upload more than one CSV.

    if input_data_path.exists():
        df.to_csv(input_data_path, mode="a", index=False, header=False)
    else:
        df.to_csv(f"{data_dir}/input_data.csv", index=False)

    flash(f"Uploaded {file.filename}", "info")
