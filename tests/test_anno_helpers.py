from pathlib import Path
import io 
import pytest
from parkVar.utils import anno_helpers as anno
from parkVar.utils import flask_utils
from flask import Flask

class TestValidate:

    def test_validate_raises_missingfileerror_when_input_missing(self, tmp_path):
        input_path = tmp_path / 'input_data.csv'
        validator_path = tmp_path / 'validated_data.csv'

        # As input_data.csv doesn't exist, an error should be raised
        with pytest.raises(flask_utils.MissingFileError) as excinfo:
            anno._validate(input_path, validator_path)

        # Check error message is correct
        msg = str(excinfo.value)
        assert 'input_data.csv' in msg
        assert 'does not exist' in msg

    def test_validate_raises_processerror_on_bad_input(self, tmp_path):
        # Create an invalid file that will make pandas in the validate script crash normally
        input_path = tmp_path / "input_data.csv"
        input_path.write_bytes(b'\x00\xFF\x00\xFF not csv')

        validator_path = tmp_path / "validated_data.csv"

        # Validate_variants should raise an error, which is caught by _validate
        with pytest.raises(flask_utils.ProcessError) as excinfo:
            anno._validate(input_path, validator_path)

        # Check the message is correct
        assert "Validation" in str(excinfo.value)

class TestAnnotate:

    def test_annotate_raises_missingfileerror_when_input_missing(self, tmp_path):
        validate_path = tmp_path / 'validated_data.csv'
        anno_path = tmp_path / 'anno_data.csv'

        # As validate_data.csv doesn't exist, an error should be raised
        with pytest.raises(flask_utils.MissingFileError) as excinfo:
            anno._annotate(validate_path, anno_path)

        # Check error message is correct
        msg = str(excinfo.value)
        assert 'validated_data.csv' in msg
        assert 'does not exist' in msg

    def test_annotate_raises_processerror_on_bad_input(self, tmp_path):
        # Create an invalid file that will make pandas in the annotate script crash normally
        validate_path = tmp_path / "validated_data.csv"
        validate_path.write_bytes(b'\x00\xFF\x00\xFF not csv')

        anno_path = tmp_path / "anno_data.csv"

        # Annotateprocess_variants_file should raise an error, which is caught by _validate
        with pytest.raises(flask_utils.ProcessError) as excinfo:
            anno._annotate(validate_path, anno_path)

        # Check the message is correct
        assert "Annotation" in str(excinfo.value)

@pytest.fixture
def app():
    app = Flask(__name__)
    return app


class TestBuildTable:

    def test_build_table_raises_missingfileerror_if_file_missing(self, tmp_path):
        anno_path = tmp_path / 'anno_data.csv'

        with pytest.raises(flask_utils.MissingFileError) as excinfo:
            anno._build_table(anno_path)

        # Check the message is correct
        assert 'anno_data.csv' in str(excinfo.value)

    def test_build_table_raises_csvreaderror_on_read_failure(self, tmp_path):
        # Create an invalid file that will make pandas in the annotate script crash normally
        anno_path = tmp_path / "anno_data.csv"
        anno_path.write_bytes(b'\x00\xFF\x00\xFF not csv')

        # Check the bad file raises a CSVReadError
        with pytest.raises(flask_utils.CSVReadError) as excinfo:
            anno._build_table(anno_path)

        # Check the error message is correct
        assert 'anno_data.csv' in str(excinfo.value)        

    def test_build_table_returns_df_and_html_on_success(self, tmp_path, app):
        # Create a dummy CSV
        anno_path = tmp_path / 'anno_data.csv'
        csv_content = 'col1,col2\n1,2\n3,4\n'
        anno_path.write_text(csv_content, encoding='utf-8')

        # Create the dataframe and html table string using the function
        with app.app_context():
            df, table_html = anno._build_table(anno_path)

        # Check the pandas dataframe is correct
        assert list(df.columns) == ['col1', 'col2']
        assert len(df) == 2
        assert df.iloc[0]['col1'] == 1

        # Check the HTML table string is correct
        assert isinstance(table_html, str)
        assert table_html.strip() != ''
        assert 'col1' in table_html
        assert 'col2' in table_html
        assert '1' in table_html
        assert '2' in table_html
