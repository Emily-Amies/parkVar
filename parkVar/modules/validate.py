import time

import pandas as pd
import requests

from parkVar.utils.logger_config import logger

# Genome build set to "GRCh38" as default, could be made configurable in future
# versions
GENOME_BUILD = "GRCh38"


# Although variant_desc is the only parameter currently being used,
# with the other params being left as default when the function is called,
# the other params have been included to allow for future flexibility
def _call_variant_validator(
    variant_desc: str,
    genome_build: str = "GRCh38",
    transcript_model: str = "refseq",
    select_transcripts: str = "mane_select",
    checkonly: bool = False,
    liftover: bool = False,
) -> dict:

    """
    Calls the Variant Validator API LOVD endpoint with the specified parameters
    . For additional information on the LOVD endpoint parameters refer to
    Variant Validator's API documentation at:
    https://rest.variantvalidator.org/.

    Args:
        variant_desc (str): The variant description.
        genome_build (str): The genome build (default: "GRCh38").
        transcript_model (str): The transcript model (default: "all").
        select_transcripts (str): Whether to select transcripts (default:
            "all").
        checkonly (bool): Whether to return only the genomic variant
            descriptions (default: True).
        liftover (bool): Whether to perform a liftover (default: False).

    Returns:
        dict: The JSON response from the API if request is successful.
    """
    # Base URL for the API
    base_url = "https://rest.variantvalidator.org/LOVD/lovd"

    # Construct the full URL
    url = (
        f"{base_url}/{genome_build}/{variant_desc}/{transcript_model}"
        f"/{select_transcripts}/{checkonly}/{liftover}"
    )

    # Query parameters
    params = {"content-type": "application/json"}

    # Headers
    headers = {"accept": "application/json"}

    try:
        # Perform the GET request using the constructed URL, params, and
        # headers
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            # Return the JSON response
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


def _update_df_with_vv_values(
    df: pd.DataFrame,
    index: int,
    variant_desc: str,
    vv_values: dict
) -> pd.DataFrame:
    """
    Updates the DataFrame with values obtained from the Variant Validator API.

    This function updates specific columns in the DataFrame for a given row
    index based on the values provided in the `vv_values` dictionary. If a
    value is missing, the corresponding column is left unchanged, and a log
    message is generated.

    Args:
        df (pd.DataFrame): The DataFrame to update.
        index (int): The index of the row to update.
        variant_desc (str): A description of the variant, used for logging.
        vv_values (dict): A dictionary containing the values to add into the
            DataFrame. The keys should correspond to the DataFrame column
            names.

    Returns:
        None: The DataFrame is updated in place.

    Example vv_values dictionary:
        vv_values = {
            "g_hgvs": "g.12345A>T",
            "t_hgvs": None,
            "hgnc_id": "HGNC:12345",
            "symbol": "GENE1",
            "p_hgvs_tlc": "p.Ala123Thr"
        }
    """
    for key, value in vv_values.items():
        if value:
            df.at[index, key] = value
        else:
            logger.warning(
                f"Variant {variant_desc} has no associated {key} value in VV."
            )

def validate_variant(variant_csv_path: str) -> pd.DataFrame:
    """
    Reads a CSV file containing genomic variants, validates each variant using
    the Variant Validator API, and updates the DataFrame with additional
    information derived from Variant Validator.

    The function adds the following columns to the DataFrame:
        - 'genome_build': The genome build used for validation (e.g., 'GRCh38')
        - 'g_hgvs': Genomic HGVS notation for each variant.
        - 't_hgvs': Transcript HGVS notation for each variant using the MANE
                Select transcript.
        - 'hgnc_id': HGNC ID associated with the gene for each variant.
        - 'symbol': Gene symbol associated with the variant.
        - 'p_hgvs_tlc': Protein HGVS notation (three-letter code) for each
          variant.

    If a variant cannot be validated, the corresponding columns will contain
    `None`, and a warning will be logged.

    The function ensures compliance with the Variant Validator API's LOVD
    endpoint rate limit of 4 requests per second by dynamically calculating
    the time taken for each request and adding a delay if necessary.

    Args:
        variant_csv_path (str): Path to the CSV file containing variant data.
        The CSV file must have the following columns:
            - '#CHROM': Chromosome identifier
            - 'POS': Position of the variant
            - 'REF': Reference allele
            - 'ALT': Alternate allele

    Returns:
        pd.DataFrame: The updated DataFrame with the following columns:
            - '#CHROM': Chromosome identifier
            - 'POS': Position of the variant
            - 'REF': Reference allele
            - 'ALT': Alternate allele
            - 'genome_build': Genome build used for validation (e.g., 'GRCh38')
            - 'g_hgvs': Genomic HGVS notation for each variant.
            - 't_hgvs': Transcript HGVS notation for each variant.
            - 'hgnc_id': HGNC ID associated with the gene for each variant.
            - 'symbol': Gene symbol associated with the variant.
            - 'p_hgvs_tlc': Protein HGVS notation (three-letter code) for each
              variant.
    """
    logger.info("Reading in variants from CSV...")
    variant_df = pd.read_csv(variant_csv_path)
    variant_df["genome_build"] = GENOME_BUILD

    vv_values = {
        "g_hgvs": None,
        "t_hgvs": None,
        "hgnc_id": None,
        "symbol": None,
        "p_hgvs_tlc": None
    }

    # Initialise new columns for desired values to be filled in from the
    # Variant Validator API response
    for column in vv_values:
        variant_df[column] = None

    # Rate limit: 4 requests per second (delay = 1/4 = 0.25 seconds)
    min_interval = 0.25

    # Loop over each row of variant df, construct variant description from the
    # relevant columns, call the variant validator API, and store the required
    # values in their respective columns
    for index, row in variant_df.iterrows():
        variant_desc = (
            f"{row['#CHROM']}-{row['POS']}-{row['REF']}-{row['ALT']}"
        )

        start_time = time.time()
        vv_response = _call_variant_validator(
            variant_desc=variant_desc, genome_build=GENOME_BUILD
        )[variant_desc][variant_desc]

        # Check if any errors are reported by VV for the genomic variant
        # description, if none extract the required values, else log a warning
        if vv_response["genomic_variant_error"] is None:

            vv_values["g_hgvs"] = vv_response["g_hgvs"]

            # Expect there to be only one transcript (the MANE Select) returned
            # for each variant, if none or >1 record this in logs
            hgvs_t_and_p_dict = vv_response["hgvs_t_and_p"]

            if len(hgvs_t_and_p_dict) == 1:
                # Get first (and only) transcript entry
                transcript_id = next(iter(hgvs_t_and_p_dict))

                # Retrieve values
                vv_values["t_hgvs"] = hgvs_t_and_p_dict[transcript_id][
                    "t_hgvs"]

                vv_values["hgnc_id"] = hgvs_t_and_p_dict[transcript_id][
                    "gene_info"]["hgnc_id"]

                vv_values["symbol"] = hgvs_t_and_p_dict[transcript_id][
                    "gene_info"]["symbol"]

                vv_values["p_hgvs_tlc"] = hgvs_t_and_p_dict[transcript_id][
                    "p_hgvs_tlc"]

                # Insert retrieved values into the dataframe
                _update_df_with_vv_values(
                    df=variant_df,
                    index=index,
                    variant_desc=variant_desc,
                    vv_values=vv_values,
                )

            else:
                logger.warning(
                    f"Variant {variant_desc} has >1 MANE Select transcript ID "
                    "returned, expected only 1 MANE Select transcript, "
                    "no further variant information will be gathered."
                )
                continue

        else:
            logger.warning(
                f"Variant {variant_desc} could not be validated: "
                f"{vv_response['genomic_variant_error']}"
            )
            continue

        # Calculate the time taken for the request
        elapsed_time = time.time() - start_time

        # Add a delay if the request completed faster than the rate limit
        if elapsed_time < min_interval:
            time.sleep(min_interval - elapsed_time)

    logger.info("Variant validation complete.")
    return variant_df


def main():
    # Example usage
    validated_df = validate_variant("/home/greg/Downloads/Patient1.csv")
    validated_df.to_csv("validated_variants.csv")


if __name__ == "__main__":
    main()
