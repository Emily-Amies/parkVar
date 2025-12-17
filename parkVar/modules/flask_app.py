"""
Flask routes for the parkVar web interface.

This module handles:
- file upload and preview
- session refresh
- variant validation
- variant annotation
- filtering of annotated variants

Author: Emily Amies
Group: 4

Notes:
- Temporary data are written to the 'data' directory at project root
- Templates are injected via render_template_string and stored in flask_utils
"""

from pathlib import Path

from flask import (
    Flask,
    redirect,
    render_template_string,
    request,
    url_for,
)

from parkVar.utils import anno_helpers as anno
from parkVar.utils import filter_helpers as filters
from parkVar.utils import flask_utils
from parkVar.utils import upload_helpers as uploads
from parkVar.utils.logger_config import logger

# Create Flask object
app = Flask(__name__)
app.secret_key = "AGE"


@app.errorhandler(flask_utils.AppError)
def global_error_handler(e):
    """
    Handle custom AppError exceptions by rendering a user-friendly error page.

    Parameters
    ----------
    e : Exception
        The raised AppError instance.

    Returns
    -------
    tuple
        A tuple of (rendered HTML, HTTP status code).
    """
    return render_template_string(flask_utils.ERROR_TEMPLATE, msg=str(e)), 400


############################################################################
# Upload files
############################################################################


@app.route("/", methods=["GET", "POST"])
def upload():
    """
    Handle the root upload route.

    GET
    ---
    Render the upload page.

    POST
    ----
    1. Accept a file upload.
    2. Convert it to a pandas DataFrame.
    3. Persist it to the temporary data directory.
    4. Render the uploaded data as an HTML table.

    Returns
    -------
    str
        Rendered HTML for the upload / preview page.
    """

    table_html = None

    if request.method == "GET":
        return render_template_string(flask_utils.UPLOAD_TEMPLATE)

    # UPLOAD FILE
    file = uploads._upload_file(request)

    # CREATE AND MODIFY PANDAS DATAFRAME
    df = uploads._create_pandas_dataframe(file)
    logger.info("Input dataframe created")

    # CREATE TEMP DATA DIRECTORY
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    logger.info("Data directory created")

    # CHECK IF FILE HAS ALREADY BEEN UPLOADED
    uploads._check_existing_files(file, data_dir)

    # STORE DATA AS CSV
    uploads._write_to_csv(data_dir, file, df)
    logger.info("Input written to CSV")

    # CREATE TABLE
    # Render the CSV as an HTML table using the template string
    table_html = flask_utils.create_table(df)
    logger.info("HTML table created")

    return render_template_string(
        flask_utils.UPLOAD_ANNO_TEMPLATE + table_html
    )


############################################################################
# Refresh session
############################################################################


def refresh_session(data_dir):
    """
    Clear all temporary data files and redirect back to the upload page.

    Parameters
    ----------
    data_dir : pathlib.Path
        Path to the temporary data directory.

    Returns
    -------
    werkzeug.wrappers.response.Response
        Redirect response to the upload route.
    """

    # Delete all files in the temporary data directory
    for item in data_dir.glob("*"):
        try:
            item.unlink()
        except Exception as e:
            logger.error(f"Failed to delete {item}: {e}")

    logger.info("Data directory deleted")

    # Return to upload page
    return redirect(url_for("upload"))


@app.route("/refresh", methods=["POST"])
def refresh_route():
    """
    Flask route that clears the temporary data directory and refreshes the
    session.

    Returns
    -------
    werkzeug.wrappers.response.Response
        Redirect response to the upload route.
    """
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    return refresh_session(data_dir)


############################################################################
# Annotate variants
############################################################################


@app.route("/annotate", methods=["POST"])
def annotate_data():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    input_path = data_dir / 'input_data.csv'
    validator_path = data_dir / 'validated_data.csv'
    anno_path = data_dir / 'anno_data.csv'

    # Validate variants
    try:
        validate_variants(input_path, validator_path)
    except Exception as e:
        logger.error('Validation failed')
        user_msg = f'Validation failed: {e}'

        # return an HTML response with 400 (bad request)
        return render_template_string(
            '''
            <h2 style="color:crimson;">{{ msg }}</h2>
            <p><a href="/">⬅ Back to upload</a></p>
            ''',
            msg=user_msg
        ), 400

    # Annotate variants
    try:
        process_variants_file(validator_path)
    except Exception as e:
        logger.error('Annotation failed')
        user_msg = f'Annotation failed: {e}'

        # return an HTML response with 400 (bad request)
        return render_template_string(
            '''
            <h2 style="color:crimson;">{{ msg }}</h2>
            <p><a href="/">⬅ Back to upload</a></p>
            ''',
            msg=user_msg
        ), 400


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


############################################################################
# Filter by patient ID
############################################################################


@app.route("/filter", methods=["POST"])
def filter_data():
    """
    Filter annotated variant data (e.g. by patient ID) and render results.

    Workflow
    --------
    1. Load annotated data from CSV.
    2. Apply filters based on form input.
    3. Persist filtered data.
    4. Render a page showing both original and filtered tables.

    Returns
    -------
    str
        Rendered HTML for the filtered results page.
    """

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    anno_path = data_dir / "anno_data.csv"
    filtered_path = data_dir / "filtered_data.csv"

    # CREATE PANDAS DATAFRAME
    df = filters._read_anno_data(anno_path)
    logger.info("Pre-filtered dataframe created")

    filtered_df, selected_ids, applied_text = filters._filter_df(
        df, filtered_path
    )
    logger.info("Filtered dataframe created")

    return filters._show_filter_page(
        df, filtered_df, selected_ids, applied_text
    )
