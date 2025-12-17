import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

import parkVar.modules.validate as validate

TEST_DATA_DIR = Path("tests") / "test_data"


@pytest.fixture
def init_values():
    """Fixture for initial values and columns used when setting up df."""
    return {
        "genome_build": "GRCh38",
        "g_hgvs": None,
        "t_hgvs": None,
        "hgnc_id": None,
        "symbol": None,
        "p_hgvs_tlc": None,
    }


@pytest.fixture(name="df")
def setup_df(init_values):
    """Fixture to set up DataFrame for testing."""
    df = validate.setup_df(
        input_csv_path=str(TEST_DATA_DIR / "test_input.csv"),
        vv_values=init_values
    )
    return df


class TestSetupDf:
    """Tests for the setup_df function in parkVar.modules.validate."""
    def test_cols_initialised_correctly(self, df, init_values):
        """
        Verify expected columns are present after setup.

        Expected columns are the input CSV base columns plus the keys from
        `init_values`. The DataFrame columns list must match this expected
        ordering and set of column names.
        """
        expected_columns = ["#CHROM", "POS", "ID", "REF", "ALT"] + list(
            init_values.keys()
        )
        assert expected_columns == list(df.columns), (
            f"DataFrame columns do not match expected columns.\n"
            f"Expected: {expected_columns}\n"
            f"Found: {list(df.columns)}"
        )

    def test_values_initialised_correctly(self, df, init_values):
        """
        Check that initialization values were applied to DataFrame columns.

        The DataFrame must not be empty and, for each key in `init_values`,
        the value in the first row of that column should equal the expected
        initial value. Only the first row is checked for simplicity.
        """
        assert not df.empty, "DataFrame is empty, expected data in df"

        for col, expected_value in init_values.items():
            # Test only value in first row for simplicity
            actual_value = df.loc[0, col]

            assert actual_value == expected_value, (
                f"Column '{col}' value does not match expected initial value\n"
                f"Expected: {expected_value}\n"
                f"Found: {actual_value}"
            )


def test_construct_vv_url():
    """
    Test the construct_vv_url function for correct URL formation.

    This test checks that the URL constructed by the function matches the
    expected format given a sample variant description.
    """
    variant_desc = "17-50198002-C-A"
    expected_url = (
        "https://rest.variantvalidator.org/LOVD/lovd/GRCh38/17-50198002-C-A"
        "/refseq/mane_select/False/False"
    )

    constructed_url = validate.construct_vv_url(variant_desc)

    assert constructed_url == expected_url, (
        f"Constructed URL does not match expected URL.\n"
        f"Expected: {expected_url}\n"
        f"Found: {constructed_url}"
    )


@pytest.fixture
def mock_valid_vv_response():
    """
    Fixture to provide a mock response JSON for variant validator LOVD endpoint
    """
    fp = TEST_DATA_DIR / "valid_vv_response.json"
    return json.loads(fp.read_text())


class TestCallVariantValidator:
    """
    Tests for the call_variant_validator function in parkVar.modules.validate.
    """
    def test_get_valid_response_when_request_ok(self, mock_valid_vv_response):
        """
        This test checks that the get request response is successfully returned
        if the get request is successful (i.e. status code 200).
        """
        mock_ok_response = MagicMock()
        mock_ok_response.json.return_value = mock_valid_vv_response
        mock_ok_response.status_code = 200

        with patch(
            'parkVar.modules.validate.requests.get',
            return_value=mock_ok_response
        ):
            response_dict = validate.call_variant_validator(
                url="https://test_url/test"
                )

            assert response_dict == mock_valid_vv_response, (
                "Response dictionary does not match expected mock response."
            )

    def test_http_error_raised_on_bad_request(self):
        """
        Assert HTTPError is raised when requests.get returns non-200 status
        code.
        """
        mock_bad_response = MagicMock()
        mock_bad_response.status_code = 400

        with patch(
            'parkVar.modules.validate.requests.get',
            return_value=mock_bad_response
        ):
            with pytest.raises(requests.HTTPError):
                validate.call_variant_validator(
                    url="https://test_url/test"
                )

    def test_request_exception_reraised(self):
        """Ensure RequestException from requests.get is re-raised"""
        with patch(
            'parkVar.modules.validate.requests.get',
            side_effect=requests.exceptions.RequestException("network fail")
        ):
            with pytest.raises(requests.exceptions.RequestException):
                validate.call_variant_validator(
                    url="https://test_url/test"
                )


@pytest.fixture
def mock_genomic_var_error_vv_response():
    """
    Fixture to provide a mock response JSON for variant validator LOVD endpoint
    """
    fp = TEST_DATA_DIR / "genomic_var_error_vv_response.json"
    return json.loads(fp.read_text())


@pytest.fixture
def mock_two_transcript_error_vv_response():
    """
    Fixture to provide a mock response JSON for variant validator LOVD endpoint
    """
    fp = TEST_DATA_DIR / "two_transcript_error_vv_response.json"
    return json.loads(fp.read_text())


@pytest.fixture
def valid_parsed_vv_rspns():
    """
    Fixture to provide a valid parsed VV response dictionary.
    """
    valid_parsed_vv_rspns = {
        0: {
            "g_hgvs": "NC_000017.11:g.50198002C>A",
            "t_hgvs": "NM_000088.4:c.589G>T",
            "hgnc_id": "HGNC:2197",
            "symbol": "COL1A1",
            "p_hgvs_tlc": "NP_000079.2:p.(Gly197Cys)"
        },
        1: {
            "g_hgvs": "NC_000017.11:g.43063903G>T",
            "t_hgvs": "NM_007294.4:c.5123C>A",
            "hgnc_id": "HGNC:1100",
            "symbol": "BRCA1",
            "p_hgvs_tlc": "NP_009225.1:p.(Ala1708Glu)"
        }
    }
    return valid_parsed_vv_rspns


class TestParseVVResponse:
    """Tests for the parse_vv_response function in parkVar.modules.validate."""

    def test_correctly_parses_response(
            self,
            mock_valid_vv_response,
            valid_parsed_vv_rspns
    ):
        """
        Test that parse_vv_response correctly extracts expected fields from
        a mock Variant Validator response.
        """
        index = 0
        parsed_output = validate.parse_vv_response(
            vv_response=mock_valid_vv_response,
            index=index
        )

        assert parsed_output == valid_parsed_vv_rspns[index], (
            f"Parsed output does not match expected output.\n"
            f"Expected: {valid_parsed_vv_rspns}\n"
            f"Found: {parsed_output}"
        )

    def test_warning_given_for_genomic_variant_error(
        self,
        caplog,
        mock_genomic_var_error_vv_response
    ):
        """
        Test that a warning is logged if the 'genomic_variant_error' field
        in the VV response is not None.
        """

        validate.parse_vv_response(
            vv_response=mock_genomic_var_error_vv_response,
            index=0
        )
        assert len(caplog.records) == 1, (
            f"Expected one warning to be logged, but found"
            f" {len(caplog.records)}."
        )

        warning_message = caplog.records[0].message

        # Assert correct warning raised as two warnings could possibly be
        # raised by parse_vv_response
        pattern = r"could not be validated"
        assert re.search(pattern, warning_message)

    def test_warning_when_two_transcripts_found(
        self,
        caplog,
        mock_two_transcript_error_vv_response
    ):
        """
        Test that a warning is logged if multiple transcripts are found in
        the VV response.
        """
        validate.parse_vv_response(
            vv_response=mock_two_transcript_error_vv_response,
            index=0
        )
        assert len(caplog.records) == 1, (
            f"Expected one warning to be logged, but found"
            f" {len(caplog.records)}."
        )

        warning_message = caplog.records[0].message

        # Assert correct warning raised
        pattern = r">1"
        assert re.search(pattern, warning_message)


@pytest.fixture
def incomplete_parsed_response():
    """
    Fixture to provide an incomplete parsed VV response dictionary.
    """
    return {
        "g_hgvs": "NC_000017.11:g.50198002C>A",
        "t_hgvs": None,
        "hgnc_id": "HGNC:2197",
        "symbol": "COL1A1",
        "p_hgvs_tlc": None
    }


class TestUpdateDfWithParsedVvValues:
    """
    Tests for the update_df_with_parsed_vv_values function in
    parkVar.modules.validate.
    """
    @pytest.mark.parametrize("idx", [0, 1])
    def test_dataframe_updated_correctly(self, df, valid_parsed_vv_rspns, idx):
        """
        Test that the DataFrame is updated correctly with parsed VV values
        at different indexes.
        """
        validate.update_df_with_parsed_vv_values(
            df=df,
            index=idx,
            vv_parsed_response=valid_parsed_vv_rspns[idx]
        )

        for col, expected_value in valid_parsed_vv_rspns[idx].items():
            actual_value = df.loc[idx, col]

            assert actual_value == expected_value, (
                f"Column '{col}' value at index {idx} does not "
                f"match expected value after update.\n"
                f"Expected: {expected_value}\n"
                f"Found: {actual_value}"
            )

    def test_no_value_in_df_when_missing_value_in_parsed_response(
        self,
        df,
        incomplete_parsed_response
    ):
        """
        Test that DataFrame retains None value when parsed VV response is
        missing expected fields.
        """
        validate.update_df_with_parsed_vv_values(
            df=df,
            index=0,
            vv_parsed_response=incomplete_parsed_response
        )

        for col, expected_value in incomplete_parsed_response.items():
            actual_value = df.loc[0, col]

            assert actual_value == expected_value, (
                f"Column '{col}' value at index 0 does not "
                f"match expected value after update with incomplete "
                f"parsed response.\n"
                f"Expected: {expected_value}\n"
                f"Found: {actual_value}"
            )

    def test_warning_logged_when_missing_value_in_parsed_response(
        self,
        df,
        incomplete_parsed_response,
        caplog
    ):
        """
        Test that a warning is logged when the parsed VV response is missing
        expected fields.
        """
        validate.update_df_with_parsed_vv_values(
            df=df,
            index=0,
            vv_parsed_response=incomplete_parsed_response
        )
        none_count = sum(
            1 for v in incomplete_parsed_response.values() if v is None
        )

        assert len(caplog.records) == none_count, (
            f"Expected {none_count} warnings to be logged, but found"
            f" {len(caplog.records)}."
        )
