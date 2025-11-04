from flask import Flask, request, render_template_string
import pandas as pd
import io # Needed for StringIO - used to make a file-like object in memory


# Create Flask object
app = Flask(__name__)

# From ChatGPT - this is the HTML template for an form. 
# <h1> - header for the page
# form - create form
#   method = 'POST' - sends to the server
#   enctype = required for file uploads
#       imput type = restrict to csv files
#       button type = adds a buttons called 'submit' and 'upload'
UPLOAD_PAGE = '''
<h1>Upload CSV</h1>
<form method='POST' enctype='multipart/form-data'>
  <input type='file' name='file' accept='.csv' required>
  <button type='submit'>Upload</button>
</form>
'''

# Defines what the app does when someone visits the root URL '/'
@app.route('/', methods=['GET', 'POST'])
def upload():
    # GET - Show the form
    if request.method == 'GET':
        # Render the HTML template from a string rather than a file
        return render_template_string(UPLOAD_PAGE)

    # Flask object that holds the file, loos for input field named 'file'
    # from the HTML form
    file = request.files.get('file')
    # If no file is provided, sends a message and HTML status code 400
    # (bad request)
    if not file or file.filename == '':
        return 'No file uploaded', 400

    try:
        # Read the raw bytes from the file object (that is encoded in UTF-8)
        text = file.read().decode('utf-8') 
        # Read file into a pandas data frame
        # io.StringIO - pandas usually expects a file on disk. When a file is
        # read using a form, it is only raw bytes in memory. StringIO creates
        # an in-memory file-object that acts like a normal file
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:
        return f'Failed to read CSV: {e}', 400

    # Render the CSV as an HTML table using the template string
    return render_template_string(
        # Template for table
        '<h1>Preview</h1><p>Rows: {{ n }}</p>{{ table|safe }}<hr>' + UPLOAD_PAGE,
        n=len(df), # Number of rows
        # Convert the pandas dataframe into simple HTML table
        table=df.to_html(index=False) # index=False - remove the index column
    )

if __name__ == '__main__':
    app.debug = True
    app.run(host = '127.0.0.1', port = 5000)
    #app.run(host='127.0.0.1', port=5000, debug=False)



