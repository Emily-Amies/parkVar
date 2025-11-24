from flask import Flask, request, render_template_string, flash, redirect, url_for
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from parkVar.utils.logger_config import logger
from parkVar.utils import upload_helpers as uploads


def _upload_file(request):
    # What happens when user uploads a file
    if request.method == "POST":
        # Flask object that holds the file, looks for input field named 'file'
        # from the HTML form
        file = request.files.get("file")

    # If no file is provided, sends a message and HTML status code 400
    # (bad request)
    if not file or file.filename == "":
        logger.warning(f"{filename} not found")
        flash('No file uploaded', 'warning')
        # Go back to the upload page
        return render_template_string(flask_utils.UPLOAD_TEMPLATE), 400
    
    return file

def _create_pandas_dataframe(file):
    # Convert file object to a pandas dataframe
    try:
        text = file.read().decode("utf-8")
        # io.StringIO - pandas usually expects a file on disk. When a file is
        # read using a form, it is only raw bytes in memory. StringIO creates
        # an in-memory file-object that acts like a normal file
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise flask_utils.CSVReadError(
            context = file.filename,
            original_exception=e
    )

    # Add patient ID as first column
    patient_id = Path(file.filename).stem # strips .csv
    if 'Patient_ID' in df.columns:
        df = df.drop(columns=['Patient_ID'])
    df.insert(0, 'Patient_ID', patient_id)

    # Remove ID column
    if 'ID' in df.columns:
        df = df.drop(columns=['ID'])

    return df

def _check_existing_files(file, data_dir):
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
    uploaded_files.write_text("\n".join(sorted(filenames)), \
    encoding="utf-8")
    

def _write_to_csv(data_dir, file, df):

    # CSV file to store the input data
    input_data_path = data_dir / "input_data.csv"

    # This will save the dataframe as a CSV in a temporary data file.
    # It will append the CSV to existing CSVs if present. This means the user
    # can upload more than one CSV.

    if input_data_path.exists():
        df.to_csv(input_data_path, mode="a", index=False, header=False)
    else:
        df.to_csv(f"{data_dir}/input_data.csv", index=False)

    # Check input file exists
    if not input_data_path.exists():
        raise flask_utils.MissingFileError(
            context='input_data.csv',
            original_exception=FileNotFoundError(f'{context} does not exist')
        )

    logger.info(f"Added file: {file.filename}")
    flash(f"Uploaded {file.filename}", "info")
