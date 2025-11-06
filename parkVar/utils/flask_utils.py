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

<form action='/refresh' method='post' style='margin-bottom: 1rem;'>
    <button type='submit'>Refresh session</button>
</form>
"""

UPLOAD_TEMPLATE = UPLOAD_PAGE + """
        <h1>Upload CSV</h1>

        <form method='POST' enctype='multipart/form-data'>
            <input type='file' name='file' accept='.csv' required>
            <button type='submit'>Upload</button>
        </form>

        <form action='/annotate' method='post' style='margin-top: 1rem;'>
            <button type='submit'>Annotate data</button>
        </form>
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
            <button type='submit' style='margin-top: 1rem;'>Apply filter</button>
        </form>

        <hr>
        <h2>Filtered data</h2>
        {{ table|safe }}
        '''

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
        "<h1>Preview</h1><p>Rows: {{ n }}</p>{{ table|safe }}<hr>" + UPLOAD_TEMPLATE,
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

def show_checkboxes(table_html, patient_ids, selected_ids=None):
    selected_ids = set(selected_ids or [])

    return render_template_string(
        UPLOAD_PAGE + '''
        <hr>
        <h2>Annotated data</h2>
        {{ table|safe }}

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
        ''',
        table=table_html,
        patient_ids=patient_ids,
        selected_ids=selected_ids,
        show_upload=False   # hide the upload UI on this page
    )