import io
import pytest
from flask import Flask, request, get_flashed_messages
from parkVar.utils import upload_helpers as uploads
from parkVar.utils import flask_utils
import pandas as pd

# Create flask app context - from ChatGPT
@pytest.fixture
def app_upload():
    app = Flask(__name__)
    app.secret_key = "testing"   # required for flash()
    return app

class TestUploadFile:

    def test_no_file_uploaded_returns_400(self, app_upload):
        # From ChatGPT

        # An error HTML and error status code is returned when there is no
        # file. Assign these as "response" and "status".
        with app_upload.test_request_context("/", method="POST", data={}):
            response, status = uploads._upload_file(request)

            # Check the error response code
            assert status == 400
            assert "No file uploaded" in response

            # Check the flash message is displayed
            flashed = get_flashed_messages(with_categories=True)
            assert ("warning", "No file uploaded") in flashed

    def test_upload_success_returns_file(self, app_upload):
        # From ChatGPT

        # Create dummy file called 'test.csv' containing a bytes string
        data = {
            "file": (io.BytesIO(b"hello world"), "test.csv")
        }

        # File is returned when a file is provided. Store as "file".
        with app_upload.test_request_context("/", method="POST", data=data):
            file = uploads._upload_file(request)

            # "file" is a FileStorage object so has the "filename" attribute
            assert file.filename == "test.csv"

            # Important: rewind before reading again
            file.stream.seek(0)

            # Check the contents is correct
            assert file.read() == b"hello world"

class TestCreatePandasDataframe:

    def test_creates_dataframe_and_inserts_patient_id(self):
        # Create a dummy CsV
        csv_content = 'col1,col2\n1,2\n3,4\n'

        # Create a dummy file from CSV
        fake_file = io.BytesIO(csv_content.encode('utf-8'))

        # Name the dummy file
        fake_file.filename = 'P123.csv'

        # Create pandas dataframe using the function
        df = uploads._create_pandas_dataframe(fake_file)

        # Patient_ID added as first column
        assert list(df.columns) == ['Patient_ID', 'col1', 'col2']
        assert df['Patient_ID'].tolist() == ['P123', 'P123']
        assert df['col1'].tolist() == [1, 3]
        assert df['col2'].tolist() == [2, 4]

    def test_overwrites_existing_patient_id_with_filename(self):
        # Create dummy CSV
        csv_content = 'Patient_ID,col1\nOLD1,10\nOLD2,20\n'

        # Create dumym file from CSV
        fake_file = io.BytesIO(csv_content.encode('utf-8'))

        # Name the dummy file
        fake_file.filename = 'NEWPAT.csv'

        # Create pandas dataframe using the function
        df = uploads._create_pandas_dataframe(fake_file)

        # Old Patient_ID column removed, new one inserted from filename
        assert list(df.columns) == ['Patient_ID', 'col1']
        assert df['Patient_ID'].tolist() == ['NEWPAT', 'NEWPAT']
        assert df['col1'].tolist() == [10, 20]

    def test_drops_id_column_if_present(self):
        # Create dummy CSV
        csv_content = 'ID,col1,col2\n10,1,2\n11,3,4\n'

        # Create dummy file from CSV
        fake_file = io.BytesIO(csv_content.encode('utf-8'))

        # Name dummy file
        fake_file.filename = 'P999.csv'

        # Create pandas dataframe using funtion
        df = uploads._create_pandas_dataframe(fake_file)

        # ID is not in the column names
        assert 'ID' not in df.columns
        assert list(df.columns) == ['Patient_ID', 'col1', 'col2']
        assert df['Patient_ID'].tolist() == ['P999', 'P999']

    def test_raises_csvreaderror(self):
        # Create a bad file
        fake_file = io.BytesIO(b'\xff\xfe\xfa') # ChatGPT

        # Name the bad file
        fake_file.filename = 'bad.csv'

        # Check the bad file raises a CSVReadError
        with pytest.raises(flask_utils.CSVReadError) as excinfo:
            uploads._create_pandas_dataframe(fake_file)

        # Check the error message is correct
        assert 'bad.csv' in str(excinfo.value)


@pytest.fixture
def app_exist(tmp_path):
    """Provide Flask app & a fresh temp directory for uploaded_files.txt."""
    app = Flask(__name__)
    app.secret_key = "testing"

    # make a temp data_dir for each test
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    return app, data_dir


class TestCheckExistingFiles:

    def test_first_upload_creates_file_and_returns_none(self, app_exist):
        app_exist, data_dir = app_exist

        # Create a dummy file
        fake_file = io.BytesIO(b"hi")
        
        # Name the dummy file
        fake_file.filename = "example.csv"

        # Filename has not already been uploaded so "result" should = None
        with app_exist.test_request_context("/", method="POST"):
            result = uploads._check_existing_files(fake_file, data_dir)

            # Should NOT return template for first upload
            assert result is None

            # Check uploaded_files.txt exists
            uploaded_file = data_dir / "uploaded_files.txt"
            assert uploaded_file.exists()

            # Check uploaded_files.txt contains the uploaded file
            contents = uploaded_file.read_text().strip()
            assert contents == "example.csv"

            # No flash messages on first upload - ChatGPT
            assert get_flashed_messages(with_categories=True) == []

    def test_duplicate_upload_returns_template_and_flashes(self, app_exist):
        app_exist, data_dir = app_exist

        # Pre-create uploaded_files.txt
        uploaded_file = data_dir / "uploaded_files.txt"
        uploaded_file.write_text("example.csv\n", encoding="utf-8")

        # Make new dummy file
        fake_file = io.BytesIO(b"hi again")
        fake_file.filename = "example.csv"

        # A new file is uploaded but already exists so "result" should = 
        # a string
        with app_exist.test_request_context("/", method="POST"):
            result = uploads._check_existing_files(fake_file, data_dir)

            # Check it returns an HTML string
            assert isinstance(result, str)
            assert "has already been uploaded" in result

            # Flash message present - ChatGPT
            flashed = get_flashed_messages(with_categories=True)
            assert ("warning", "⚠ example.csv has already been uploaded") in flashed

    def test_upload_appends_new_filename(self, app_exist):
        app_exist, data_dir = app_exist

        # Pre-create uploaded_files.txt
        uploaded_file = data_dir / "uploaded_files.txt"
        uploaded_file.write_text("a.csv\nb.csv\n", encoding="utf-8")

        # Make new different file
        fake_file = io.BytesIO(b"x")
        fake_file.filename = "c.csv"

        # Filename has not already been uploaded so "result" should = None
        with app_exist.test_request_context("/", method="POST"):
            result = uploads._check_existing_files(fake_file, data_dir)

            assert result is None

            # Check new file has been added to the list
            contents = uploaded_file.read_text().splitlines()
            assert contents == ["a.csv", "b.csv", "c.csv"]

@pytest.fixture
def app_write(tmp_path):
    app = Flask(__name__)
    app.secret_key = 'testing'  # needed for flash()

    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    return app, data_dir

class TestWriteToCsv:

    def test_creates_new_csv_and_flashes(self, app_write):
        app_write, data_dir = app_write

        # Create dummy pandas datarame
        df = pd.DataFrame({'Patient_ID': ['P1'], 'col1': [123]})

        # Make a dummy file to get name from
        fake_file = io.BytesIO(b"")
        fake_file.filename = "test.csv"

        # Write pandas dataframe 
        with app_write.test_request_context('/', method='POST'):
            uploads._write_to_csv(data_dir, fake_file, df)

            # Check the new input file exists
            input_data_path = data_dir / 'input_data.csv'
            assert input_data_path.exists()

            # Read lines from the file into a list
            lines = input_data_path.read_text().strip().splitlines()
            
            # Check the contents of the file is correct
            assert len(lines) == 2
            assert 'Patient_ID' in lines[0]
            assert 'col1' in lines[0]
            assert 'P1' in lines[1]
            assert '123' in lines[1]

            # Check the flash message appears - ChatGPT
            flashed = get_flashed_messages(with_categories=True)
            assert ('info', 'Uploaded test.csv') in flashed

    def test_appends_to_existing_csv(self, app_write):
        app_write, data_dir = app_write

        input_data_path = data_dir / 'input_data.csv'

        # Create an existing CSV file
        existing = pd.DataFrame({'Patient_ID': ['OLD'], 'col1': [1]})
        existing.to_csv(input_data_path, index=False)

        # Dataframe with new data
        new_df = pd.DataFrame({'Patient_ID': ['NEW'], 'col1': [2]})

        # Create fake input file to get name from
        fake_file = io.BytesIO(b"")
        fake_file.filename = "new.csv"

        with app_write.test_request_context('/', method='POST'):
            uploads._write_to_csv(data_dir, fake_file, new_df)

            # Read lines to a list
            lines = input_data_path.read_text().strip().splitlines()

            # One header + two data rows
            assert len(lines) == 3

            # Header
            assert 'Patient_ID' in lines[0]
            assert 'col1' in lines[0]

            # Row with old data
            assert 'OLD' in lines[1]
            assert '1' in lines[1]

            # Appended row (no second header)
            assert 'NEW' in lines[2]
            assert '2' in lines[2]

            # Flash message shown - ChatGPT
            flashed = get_flashed_messages(with_categories=True)
            assert ('info', 'Uploaded new.csv') in flashed
