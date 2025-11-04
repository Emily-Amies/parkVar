from flask import Flask, request, render_template_string
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from datetime import datetime


# Create Flask object
app = Flask(__name__)


# Defines what the app does when someone visits the root URL '/'
@app.route("/", methods=["GET", "POST"])
def upload():
    # GET - Show the form
    if request.method == "GET":
        # Render the HTML template from a string rather than a file
        return render_template_string(flask_utils.UPLOAD_PAGE)

    # Flask object that holds the file, loos for input field named 'file'
    # from the HTML form
    file = request.files.get("file")
    # If no file is provided, sends a message and HTML status code 400
    # (bad request)
    if not file or file.filename == "":
        return "No file uploaded", 400

    try:
        df = flask_utils.create_df(file)
    except Exception as e:
        return f"Failed to read CSV: {e}", 400

    # Create a temporary directory to store data
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    input_data_path = data_dir / "input_data.csv"

    # This will save the dataframe as a CSV in a temporary data file.
    # It will append the CSV to existing CSVs if present. This means the user
    # can upload more than one CSV.
    if input_data_path.exists():
        df.to_csv(input_data_path, mode="a", index=False, header=False)
    else:
        df.to_csv(f"{data_dir}/input_data.csv", index=False)

    # Render the CSV as an HTML table using the template string
    return flask_utils.create_table(df)


if __name__ == "__main__":
    app.debug = True
    app.run(host="127.0.0.1", port=5000)
