from flask import Flask, request, render_template_string
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory

# From ChatGPT - this is the HTML template for an form.
# <h1> - header for the page
# form - create form
#   method = 'POST' - sends to the server
#   enctype = required for file uploads
#       imput type = restrict to csv files
#       button type = adds a buttons called 'submit' and 'upload'
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

<h1>Upload CSV</h1>

<form method='POST' enctype='multipart/form-data'>
  <input type='file' name='file' accept='.csv' required>
  <button type='submit'>Upload</button>
</form>

<form action='/refresh' method='post' style='margin-top: 1rem;'>
  <button type='submit'>Refresh session</button>
</form>

"""


def create_df(file):
    # Read the raw bytes from the file object (that is encoded in UTF-8)
    text = file.read().decode("utf-8")
    # Read file into a pandas data frame
    # io.StringIO - pandas usually expects a file on disk. When a file is
    # read using a form, it is only raw bytes in memory. StringIO creates
    # an in-memory file-object that acts like a normal file
    df = pd.read_csv(io.StringIO(text))
    return df


def create_table(df):
    table = render_template_string(
        # Template for table
        "<h1>Preview</h1><p>Rows: {{ n }}</p>{{ table|safe }}<hr>" + UPLOAD_PAGE,
        n=len(df),  # Number of rows
        # Convert the pandas dataframe into simple HTML table
        table=df.to_html(index=False),  # index=False - remove the index column
    )
    return table


def load_uploaded_filenames(uploaded_files):
    if not uploaded_files.exists():
        return list()
    return [
        line.strip()
        for line in uploaded_files.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def save_uploaded_filenames(uploaded_files, filenames: list):
    uploaded_files.write_text("\n".join(sorted(filenames)), encoding="utf-8")

def refresh_session(data_dir):
    for item in data_dir.glob('*'):
        try:
            item.unlink()
        except Exception as e:
            logger.error(f'Failed to delete {item}: {e}')
    return redirect(url_for('/'))