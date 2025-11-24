from flask import Flask, request, render_template_string, flash, redirect, url_for
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from parkVar.utils.logger_config import logger
from parkVar.utils import upload_helpers as uploads
from parkVar.utils import anno_helpers as anno
from parkVar.utils import filter_helpers as filters
from parkVar.modules.validate import validate_variants
from parkVar.modules.clinvar_annotator import process_variants_file

# Create Flask object
app = Flask(__name__)
app.secret_key = "AGE"

# Error handler - renders a more user-friendly error page if an exception
# is encountered. Use AppError so applies to all custom exceptions.
@app.errorhandler(flask_utils.AppError)
def global_error_handler(e):
    return render_template_string(
        flask_utils.ERROR_TEMPLATE,
        msg=str(e)
    ), 400

############################################################################
# Upload files
############################################################################

# Defines what the app does when someone visits the root URL '/'
@app.route("/", methods=["GET", "POST"])
def upload():

    table_html = None

    # LANDING PAGE
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
    filenames = uploads._check_existing_files(file, data_dir)

    # STORE DATA AS CSV
    uploads._write_to_csv(data_dir, file, df)
    logger.info("Input written to CSV")

    # CREATE TABLE
    # Render the CSV as an HTML table using the template string
    table_html = flask_utils.create_table(df)
    logger.info("HTML table created")

    return render_template_string(flask_utils.UPLOAD_ANNO_TEMPLATE + table_html)


############################################################################
# Refresh session
############################################################################

@app.route('/refresh', methods=['POST'])
def refresh_session():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    # Delete all files in the temporary data directory
    for item in data_dir.glob('*'):
        try:
            item.unlink()
        except Exception as e:
            logger.error(f'Failed to delete {item}: {e}')
    logger.info("Data directory deleted")
    # Return to upload page
    return redirect(url_for('upload'))

############################################################################
# Annotate variants
############################################################################

@app.route('/annotate', methods=['POST'])
def annotate_data():

    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    input_path = data_dir / 'input_data.csv'
    validator_path = data_dir / 'validated_data.csv'
    anno_path = data_dir / 'anno_data.csv'

    # VALIDATE DATA
    anno._validate(input_path, validator_path)
    logger.info("Validator script run sucessfully")

    # ANNOTATE DATA
    anno._annotate(validator_path, anno_path)
    logger.info("Annotator script run sucessfully")

    # BUILD HTML TABLE
    df, table_html = anno._build_table(anno_path)
    logger.info("Annotated table built")

    # SHOW ANNOTATED DATA AND CHECKBOXES FOR FILTERING
    return flask_utils.show_checkboxes(df, table_html)

############################################################################
# Filter by patient ID
############################################################################

@app.route('/filter', methods=['POST'])
def filter_data():
    data_dir = Path(__file__).resolve().parent.parent.parent / 'data'
    anno_path = data_dir / 'anno_data.csv'
    filtered_path = data_dir / 'filtered_data.csv'

    # CREATE PANDAS DATAFRAME
    df = filters._read_anno_data(anno_path)
    logger.info("Pre-filtered dataframe created")

    filtered_df, selected_ids, applied_text = filters._filter_df(df, filtered_path)
    logger.info("Filtered dataframe created")

    return filters._show_filter_page(df, filtered_df, selected_ids, applied_text)
