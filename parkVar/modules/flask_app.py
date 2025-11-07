from flask import Flask, request, render_template_string, flash, redirect, url_for
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from parkVar.utils.logger_config import logger


# Create Flask object
app = Flask(__name__)
app.secret_key = "AGE"


# Defines what the app does when someone visits the root URL '/'
@app.route("/", methods=["GET", "POST"])
def upload():
    # GET - Show the form
    if request.method == "GET":
        # Render the HTML template from a string rather than a file
        return render_template_string(flask_utils.UPLOAD_TEMPLATE)


    ##########################################################################
    # Load in files
    ##########################################################################

    # Flask object that holds the file, loos for input field named 'file'
    # from the HTML form
    file = request.files.get("file")
    filename = file.filename

    # If no file is provided, sends a message and HTML status code 400
    # (bad request)
    if not file or file.filename == "":
        logger.warning(f"{filename} not found")
        return "No file uploaded", 400

    # Convert file object to a pandas dataframe
    try:
        df = flask_utils.create_df(file)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return f"Failed to read CSV: {e}", 400

    # Add patient ID column

    # Add patient ID as first column
    patient_id = Path(filename).stem # strips .csv
    if 'Patient_ID' in df.columns:
        df = df.drop(columns=['Patient_ID'])
    df.insert(0, 'Patient_ID', patient_id)

    ##########################################################################
    # Save data to temporary data file
    ##########################################################################

    # Create a temporary directory to store data
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    # If the directory already exists, delete it to start a fresh session
    data_dir.mkdir(exist_ok=True)

    # CSV file to store the input data
    input_data_path = data_dir / "input_data.csv"

    # File to store filenames that have been uploaded this session
    uploaded_files = Path(data_dir / "uploaded_files.txt")
    # Create a list from the file of uploaded filenames
    filenames = flask_utils.load_uploaded_filenames(uploaded_files)

    # This will save the dataframe as a CSV in a temporary data file.
    # It will append the CSV to existing CSVs if present. This means the user
    # can upload more than one CSV.
    if filename in filenames:
        logger.warning(f"{filename} already uploaded")
        flash(f"⚠ {filename} has already been uploaded", "warning")
    else:
        if input_data_path.exists():
            df.to_csv(input_data_path, mode="a", index=False, header=False)
            logger.info(f"Added file: {filename}")
            flash(f"Uploaded {filename}", "info")
            filenames.append(filename)
        else:
            df.to_csv(f"{data_dir}/input_data.csv", index=False)
            logger.info(f"Added file: {filename}")
            flash(f"Uploaded {filename}", "info")
            filenames.append(filename)

    flask_utils.save_uploaded_filenames(uploaded_files, filenames)

    # Render the CSV as an HTML table using the template string
    return flask_utils.create_table(df)


@app.route('/refresh', methods=['POST'])
def refresh_session():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    for item in data_dir.glob('*'):
        try:
            item.unlink()
        except Exception as e:
            logger.error(f'Failed to delete {item}: {e}')
    return redirect(url_for('upload'))

@app.route('/annotate', methods=['POST'])
def annotate_data():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    anno_path = data_dir / 'anno_data.csv'

    if not anno_path.exists():
        return 'Annotated file not found. Did the annotation step run?', 400

    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        logger.error(f'Failed to read anno_data.csv: {e}')
        return f'Failed to read anno_data.csv: {e}', 500

    logger.info(f'Loaded annotated data with {len(df)} rows')

    # build HTML table
    table_html = flask_utils.create_table(df)

    # get unique patient IDs for checkboxes
    if 'Patient_ID' in df.columns:
        patient_ids = sorted(df['Patient_ID'].astype(str).dropna().unique().tolist())
    else:
        logger.error('Patient_ID column missing from annotated data')
        return 'Patient_ID column missing from annotated data', 400

    # return a page with table + checkbox filter form
    return flask_utils.show_checkboxes(table_html, patient_ids)

@app.route('/filter', methods=['POST'])
def filter_data():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    anno_path = data_dir / 'anno_data.csv'
    filtered_path = data_dir / 'filtered_data.csv'

    # decide which file we are filtering (anno_data.csv should exist at this point)
    if not anno_path.exists():
        logger.error('Annotated file not found when filtering')
        return 'Annotated file not found. Run annotation first.', 400

    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        logger.error(f'Failed to read anno_data.csv during filtering: {e}')
        return f'Failed to read anno_data.csv: {e}', 500

    if 'Patient_ID' not in df.columns:
        logger.error('Patient_ID column missing when filtering')
        return 'Patient_ID column missing from data', 400

    # list of selected patient IDs from the form
    selected_ids = request.form.getlist('patient_id')

    # apply filter
    if selected_ids:
        filtered_df = df[df['Patient_ID'].astype(str).isin(selected_ids)]
        logger.info(f'Filter applied to Patient_ID(s): {selected_ids}')
        applied_text = f'Filtered to: {", ".join(selected_ids)}'
    else:
        # no boxes ticked = show everything
        filtered_df = df.copy()
        logger.info('No filter applied (no Patient_ID selected)')
        applied_text = 'No filter selected. Showing all rows.'

    # write filtered CSV
    filtered_df.to_csv(filtered_path, index=False)

    # rebuild checkbox values so the page can re-render them
    patient_ids = sorted(df['Patient_ID'].astype(str).dropna().unique().tolist())

    # Build the table HTML for the filtered frame
    table_html = flask_utils.create_table(filtered_df)

    return render_template_string(
        flask_utils.ANNO_TEMPLATE,
        applied_text=applied_text,
        table=table_html,
        patient_ids=patient_ids,
        selected_ids=selected_ids
    )


if __name__ == "__main__":
    app.debug = True
    app.run(host="127.0.0.1", port=5000)

# lsof -i :5000
# kill -9 <id>
