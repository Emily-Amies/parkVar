from flask import Flask, request, render_template_string, flash
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
        return render_template_string(flask_utils.UPLOAD_PAGE)

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


if __name__ == "__main__":
    app.debug = True
    app.run(host="127.0.0.1", port=5000)

# lsof -i :5000
# kill -9 <id>
