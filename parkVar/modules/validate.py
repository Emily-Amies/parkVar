import sys
import time
from typing import Any, Dict, Optional

import pandas as pd
import requests

from parkVar.utils.logger_config import logger

# Genome build set to "GRCh38" as default, could be made configurable in future
# versions
GENOME_BUILD = "GRCh38"


def setup_df(input_csv_path: str, vv_values: dict) -> pd.DataFrame:
    """
    Reads a CSV file containing genomic variants and initialises a DataFrame
    with additional columns for Variant Validator values.

    This function reads the input CSV file into a DataFrame, adds a
    'genome_build' column with a default value, and initializes additional
    columns for values to be filled in from the Variant Validator API.

    Args:
        input_csv_path (str): Path to the input CSV file containing variant
            data. The CSV file must have the following columns:
            - '#CHROM': Chromosome identifier.
            - 'POS': Position of the variant.
            - 'REF': Reference allele.
            - 'ALT': Alternate allele.
        vv_values (dict): A dictionary defining the columns to be added to the
            DataFrame and their default values. Keys are column names, and
            values are the default values for those columns.

    Returns:
        pd.DataFrame: A DataFrame containing the input data with additional
        columns initialized for Variant Validator values.
    """

    logger.info(f"Reading in variants from {input_csv_path}")
    variant_df = pd.read_csv(input_csv_path)

    # Initialise new columns for desired values to be filled in from the
    # Variant Validator API response
    for column_name, default_value in vv_values.items():
        variant_df[column_name] = default_value

    return variant_df


# Although variant_desc is the only parameter currently being used,
# with the other params being left as default when the function is called,
# the other params have been included to allow for future flexibility
def construct_vv_url(
    variant_desc: str,
    base_url: str = "https://rest.variantvalidator.org/LOVD/lovd",
    genome_build: str = GENOME_BUILD,
    transcript_model: str = "refseq",
    select_transcripts: str = "mane_select",
    checkonly: bool = False,
    liftover: bool = False
) -> str:
    """
    Construct a Variant Validator LOVD endpoint URL.

    Build a full LOVD URL from a variant description and optional flags, to be
    used for querying the Variant Validator API via "call_variant_validator".

    Args:
        variant_desc (str): Variant description (e.g. "1-100-A-T").
        base_url (str): Base LOVD endpoint (default provided).
        genome_build (str): Genome build identifier (default: GENOME_BUILD).
        transcript_model (str): Transcript model (default: "refseq").
        select_transcripts (str): Transcript selection mode (default:
            "mane_select").
        checkonly (bool): If True, request check-only behaviour (default:
            False).
        liftover (bool): If True, perform liftover (default: False).

    Returns:
        str: Fully constructed LOVD URL.
    """
    # Construct the full URL from function parameters + base URL
    url = (
        f"{base_url}/{genome_build}/{variant_desc}/{transcript_model}"
        f"/{select_transcripts}/{checkonly}/{liftover}"
    )
    return url


def call_variant_validator(url: str) -> dict:
    """
    Call the Variant Validator LOVD endpoint and return parsed JSON.

    Given a URL, send a GET request and return the
    JSON body when the response status is 200. Non-200 responses are logged
    and an HTTPError is raised. Network/request exceptions are logged and
    re-raised.

    Args:
        url (str): Full LOVD endpoint URL to request.

    Returns:
        dict: JSON response on successful request (i.e. status code 200).
    """

    params = {"content-type": "application/json"}
    headers = {"accept": "application/json"}

    try:
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            return response.json()

        # Log and raise an error for any status code that is not 200, as this
        # is the only status code we expect for a successful request
        logger.error(
            f"Error: Received status code {response.status_code} - "
            f"{response.text}"
        )

        raise requests.exceptions.HTTPError(
            f"Unexpected status code {response.status_code}: {response.text}"
        )

    # Catch, log and raise any non status code related errors that would be
    # missed in the above error handling
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise e


def bulk_call_variant_validator(
    variant_df: pd.DataFrame,
    min_interval: float = 0.25
) -> Dict[int, dict]:
    """
    Call Variant Validator (VV) for each variant in a DataFrame, respecting a
    minimum inter-request interval given in seconds.

    For every row in `variant_df` a variant description is built from the
    '#CHROM', 'POS', 'REF' and 'ALT' columns. Each variant is requested
    via `call_variant_validator` and the VV response is stored in a dict
    keyed by the DataFrame row index.

    If a request completes faster than `min_interval` seconds, the function
    sleeps the remaining time so the effective request rate does not
    exceed the intended frequency.

    Args:
        variant_df (pd.DataFrame): DataFrame containing '#CHROM', 'POS',
            'REF' and 'ALT' columns.
        min_interval (float): Minimum seconds to wait between requests.

    Returns:
        Dict[int, dict]: Mapping from DataFrame row index to the Variant
            Validator response dict for that variant.
    """
    vv_responses = {}

    # Loop over each row of variant df, construct variant description from the
    # relevant columns, call the variant validator API, and store the required
    # values in their respective columns
    for index, row in variant_df.iterrows():
        variant_desc = (
            f"{row['#CHROM']}-{row['POS']}-{row['REF']}-{row['ALT']}"
        )

        url = construct_vv_url(variant_desc=variant_desc)

        start_time = time.time()

        vv_responses[index] = call_variant_validator(url=url)[variant_desc][
            variant_desc]

        # Calculate the time taken for the request
        elapsed_time = time.time() - start_time

        # Add a delay if the request completed faster than the rate limit
        if elapsed_time < min_interval:
            time.sleep(min_interval - elapsed_time)

    return vv_responses


def parse_vv_response(
        vv_response: dict,
        index: int
) -> Optional[Dict[str, Any]]:
    """
    Parse a Variant Validator (VV) response for one variant row.

    Returns a dict with keys "g_hgvs", "t_hgvs", "hgnc_id", "symbol" and
    "p_hgvs_tlc" when the genomic description has no error and exactly one
    transcript entry is present. If the genomic validation reports an error
    or if zero or multiple transcripts are present, a warning is logged and
    None is returned.

    Args:
        vv_response (dict): Single-variant response from Variant Validator.
        index (int): Row index in the source DataFrame, used for logging.

    Returns:
        dict or None: Parsed values on success, otherwise None.
    """

    vv_parsed_response = {}

    # Check if any errors are reported by VV for the genomic variant
    # description, if none extract the required values, else log a warning
    if vv_response["genomic_variant_error"] is None:

        vv_parsed_response["g_hgvs"] = vv_response["g_hgvs"]

        # Expect there to be only one transcript (the MANE Select) returned
        # for each variant, if none or >1 record this in logs
        hgvs_t_and_p_dict = vv_response["hgvs_t_and_p"]

        if len(hgvs_t_and_p_dict) == 1:
            # Get first (and only) transcript entry
            transcript_id = next(iter(hgvs_t_and_p_dict))

            # Retrieve values from VV response
            vv_parsed_response["t_hgvs"] = hgvs_t_and_p_dict[transcript_id][
                "t_hgvs"]

            vv_parsed_response["hgnc_id"] = hgvs_t_and_p_dict[transcript_id][
                "gene_info"]["hgnc_id"]

            vv_parsed_response["symbol"] = hgvs_t_and_p_dict[transcript_id][
                "gene_info"]["symbol"]

            vv_parsed_response["p_hgvs_tlc"] = hgvs_t_and_p_dict[
                transcript_id]["p_hgvs_tlc"]

            return vv_parsed_response

        else:
            logger.warning(
                f"Variant at row {index} has >1 MANE Select transcript ID "
                "returned, expected only 1 MANE Select transcript, "
                "no further variant information will be gathered."
            )
            return

    else:
        logger.warning(
            f"Variant at row {index} could not be validated: "
            f"{vv_response['genomic_variant_error']}"
        )
        return


def update_df_with_parsed_vv_values(
    df: pd.DataFrame,
    index: int,
    vv_parsed_response: Dict[str, Any]
) -> None:
    """
    Updates a DataFrame with values obtained from the Variant Validator API.

    This function updates specific columns in the DataFrame for a given row
    index based on the values provided in the `vv_parsed_response` dictionary.
    If a value is missing, the corresponding column is left unchanged, and a
    log message is generated.

    Args:
        df (pd.DataFrame): The DataFrame to update.
        index (int): The index of the row to update.
        vv_parsed_response (dict): A dictionary containing the values to add
            into the DataFrame. The keys should correspond to the DataFrame
            column names.

    Returns:
        None: The DataFrame is updated in place.

    Example vv_parsed_response dictionary:
        vv_parsed_response = {
            "g_hgvs": "g.12345A>T",
            "t_hgvs": None,
            "hgnc_id": "HGNC:12345",
            "symbol": "GENE1",
            "p_hgvs_tlc": "p.Ala123Thr"
        }
    """
    for key, value in vv_parsed_response.items():
        if value:
            df.at[index, key] = value
        else:
            logger.warning(
                f"Variant at row {index} has no associated {key} value in VV."
            )


def validate_variants(
    input_csv_path: str,
    output_csv_path: str
) -> None:
    """
    Validate variants from an input CSV and write results to an output CSV.

    Reads variants from `input_csv_path`, adds and initializes columns used
    to store Variant Validator values, queries the Variant Validator API
    for each variant (respecting the configured rate limit), parses the
    responses, updates the DataFrame, and writes the completed table to
    `output_csv_path`.

    Args:
        input_csv_path (str): Path to the input CSV. Must contain columns
            '#CHROM', 'POS', 'REF', 'ALT'.
        output_csv_path (str): Path to write the updated CSV.

    Returns:
        None: The updated DataFrame is written to `output_csv_path`.
    """

    # Define the Variant Validator values to be extracted and their default
    # values when setting up the DataFrame
    vv_values = {
        "genome_build": GENOME_BUILD,
        "g_hgvs": None,
        "t_hgvs": None,
        "hgnc_id": None,
        "symbol": None,
        "p_hgvs_tlc": None
    }

    # Read in variant csv and add additional columns with default values as
    # specified in vv_values
    variant_df = setup_df(
        input_csv_path=input_csv_path,
        vv_values=vv_values
    )

    # Get Variant Validator responses for all variants in the DataFrame
    # stored in a dict with row index as key
    vv_responses = bulk_call_variant_validator(variant_df=variant_df)

    # Parse each VV response and update the variant DataFrame with the
    # retrieved values
    for index, vv_response in vv_responses.items():
        vv_parsed_response = parse_vv_response(
            vv_response=vv_response,
            index=index
        )
        update_df_with_parsed_vv_values(
            df=variant_df,
            index=index,
            vv_parsed_response=vv_parsed_response
        )

    variant_df.to_csv(output_csv_path, index=False)

    logger.info(
        f"Variant validation complete. Output saved to {output_csv_path}."
    )


if __name__ == "__main__":
    validate_variants(sys.argv[1], sys.argv[2])
