from flask import Flask, request, render_template_string
import pandas as pd
from parkVar.utils.logger_config import logger
import io  # Needed for StringIO - used to make a file-like object in memory


########################################################################
# HTML Templates
########################################################################

# ALL HTML TEMPLATES IN THIS DOCUMENT WERE GENERATED USING CHATGPT

# Base template - includes code for flashed messsages and the "refresh 
# sessipon" button
UPLOAD_PAGE = """
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <ul class="flashes">
            {% for category, message in messages %}
                <li class="{{ category }}">{{ message }}</li>
            {% endfor %}
            </ul>
        {% endif %}
        {% endwith %}

        <style>
            .warning {
                color: red;
                font-weight: bold;
            }

            .info {
                color: blue;
                font-weight: bold;
            }
        </style>

        <form action='/refresh' method='post' style='margin-bottom: 1rem;'>
            <button type='submit'>Refresh session</button>
        </form>
        """

# The whole template for the home upload screen. Includes buttons to browse
# and upload fines. Another button starts the validation and annotation 
# modules.
UPLOAD_TEMPLATE = UPLOAD_PAGE + """
        <h1>Welcome to ParkVar!</h1>
        <h3>Upload files</h3>

        <form method='POST' enctype='multipart/form-data'>
            <input type='file' name='file' accept='.csv' required>
            <button type='submit'>Upload</button>
        </form>
        """

UPLOAD_ANNO_TEMPLATE = UPLOAD_TEMPLATE + """
        {% if table_html %}
            <hr>
            <div>
              {{ table_html|safe }}
            </div>
        {% endif %}

        <h3>Upload more files or annotate your data</h3>
        <form action='/annotate' method='post'>
        <button type='submit' id='annotate-btn'>Annotate</button>
        </form>

        <p id='annotating-msg' style='display:none; color: red; margin-top:1rem;'>
        Annotating variants, this may take a few seconds...
        </p>

        <script>
        document.addEventListener('DOMContentLoaded', function () {
            const btn = document.getElementById('annotate-btn');
            const msg = document.getElementById('annotating-msg');

            if (btn) {
                btn.addEventListener('click', function () {
                    msg.style.display = 'block';
                });
            }
        });
        </script>

        <h3>Uploaded data</h3>
        """

ANNO_TEMPLATE = UPLOAD_PAGE + '''
        <p><em>{{ applied_text }}</em></p>

        <h3>Filter by Patient_ID</h3>
        <form action='/filter' method='post' style='margin-bottom: 1rem;'>
            {% for pid in patient_ids %}
                <label>
                    <input type='checkbox'
                           name='patient_id'
                           value='{{ pid }}'
                           {% if pid in selected_ids %}checked{% endif %}>
                    {{ pid }}
                </label><br>
            {% endfor %}
            <button type='submit' style='margin-top: 1rem;'>Filter</button>
        </form>

        <hr>
        <h2>Filtered data</h2>
        {{ table|safe }}
        '''

CHECKBOX_TEMPLATE = UPLOAD_PAGE + '''
        <h3>Filter by Patient_ID</h3>
        <form action='/filter' method='post' style='margin-top: 1rem;'>
          {% for pid in patient_ids %}
            <label>
              <input type='checkbox'
                     name='patient_id'
                     value='{{ pid }}'
                     {% if pid in selected_ids %}checked{% endif %}>
              {{ pid }}
            </label><br>
          {% endfor %}
          <button type='submit' style='margin-top: 1rem;'>Apply filter</button>
        </form>

        <hr>
        <h2>Annotated data</h2>
        {{ table|safe }}
        '''

ERROR_TEMPLATE = '''
<!doctype html>
<html>
  <head>
    <title>Error</title>
    <style>
      body {
        font-family: sans-serif;
        margin: 2rem;
      }
      .error-box {
        border: 1px solid crimson;
        padding: 1rem;
        background: #ffe6e6;
        border-radius: 6px;
      }
      h2 {
        color: crimson;
        margin-top: 0;
      }
      a {
        color: #1a73e8;
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
    </style>
  </head>
  <body>
    <div class="error-box">
      <h2>Error</h2>
      <p>{{ msg }}</p>
    </div>

    <p style="margin-top:2rem;">
      <a href="/">⬅ Back to upload</a>
    </p>
  </body>
</html>
'''

########################################################################
# Custom Exceptions
########################################################################

# Base exception
class AppError(Exception):
    pass

# CSV read error exception
class CSVReadError(AppError):
    def __init__(self, context, original_exception):
        self.context = context
        self.original_exception = original_exception

        message = f'Failure reading: {context}'
        message += f': {original_exception}'

        super().__init__(message)

        logger.error(message)

# Missing file exception
class MissingFileError(AppError):
    def __init__(self, context, original_exception):
        self.context = context
        self.original_exception = original_exception

        message = f'Could not find: {context}'
        message += f': {original_exception}'

        super().__init__(message)

        logger.error(message)

# Step in the validation or annotation process has failed
class ProcessError(AppError):
    def __init__(self, context, original_exception):
        self.context = context
        self.original_exception = original_exception

        message = f'{context} step has failed'
        message += f': {original_exception}'

        super().__init__(message)

        logger.error(message)

class MissingColumnError(AppError):
    def __init__(self, context, original_exception):
        self.context = context
        self.original_exception = original_exception

        message = f'{context} column is missing'
        message += f': {original_exception}'

        super().__init__(message)

        logger.error(message)

########################################################################
# Functions
########################################################################

# Functions that may be reused when expanding the project further

def create_table(df):
    table = render_template_string(
        # Template for table
        "<h3></h3><p>Rows: {{ n }}</p>{{ table|safe }}<hr>",
        n=len(df),  # Number of rows
        # Convert the pandas dataframe into simple HTML table
        table=df.to_html(index=False),  # index=False - remove the index column
    )
    return table

# Only used once so far, but can be altered to add additional checkboxes
def show_checkboxes(df, table_html, selected_ids=None):
    
    # Get unique patient IDs for checkboxes
    if 'Patient_ID' in df.columns:
        patient_ids = sorted(df['Patient_ID'].astype(str).dropna().unique().tolist())
    else:
        raise MissingColumnError(
            context='Patient_ID',
            original_exception=KeyError('Patient_ID')
        )

    selected_ids = set(selected_ids or [])

    return render_template_string(
        CHECKBOX_TEMPLATE,
        table=table_html,
        patient_ids=patient_ids,
        selected_ids=selected_ids,
        show_upload=False   # hide the upload UI on this page
    )