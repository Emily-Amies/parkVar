import time

import pandas as pd
import requests

from parkVar.utils.logger_config import logger

# Although variant_description is the only parameter currently being used,
# with the other params being left as default when the function is called,
# the other params have been included to allow for future flexibility
def call_variant_validator(
    variant_description: str,
    genome_build: str = "GRCh38",
    transcript_model: str = "all",
    select_transcripts: str = "all",
    checkonly: bool = True,
    liftover: bool = False,
) -> dict:

    """
    Calls the Variant Validator API LOVD endpoint with the specified parameters
    . For additional information on the LOVD endpoint parameters refer to
    Variant Validator's API documentation at:
    https://rest.variantvalidator.org/.

    Args:
        variant_description (str): The variant description.
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
        f"{base_url}/{genome_build}/{variant_description}/{transcript_model}"
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


def validate_variant(variant_csv_path: str) -> pd.DataFrame:
    """
    Reads a CSV file containing genomic variants, validates each variant using
    the Variant Validator API, and adds the g_hgvs (genomic HGVS notation) to a
    new column in the DataFrame.

    The function ensures compliance with the Variant Validator API's LOVD
    endpoint rate limit of 4 requests per second by dynamically calculating the
    time taken for each request and adding a delay if necessary.

    Args:
        variant_csv_path (str): Path to the CSV file containing variant data.
        The CSV file must have the following columns:
            - '#CHROM': Chromosome identifier
            - 'POS': Position of the variant
            - 'REF': Reference allele
            - 'ALT': Alternate allele

    Returns:
        pd.DataFrame: The updated DataFrame with a new column 'g_hgvs'
        containing the genomic HGVS notation for each variant. If a variant
        could not be validated, the 'g_hgvs' column will contain None.

    Example:
        Input CSV:
            #CHROM,POS,REF,ALT
            1,12345,A,T
            2,67890,G,C

        Output DataFrame:
            #CHROM  POS REF ALT g_hgvs
            1  12345   A   T  g.12345A>T
            2  67890   G   C  g.67890G>C
    """
    logger.info("Reading in variants from CSV...")
    variant_df = pd.read_csv(variant_csv_path)

    # Initialize a new column for g_hgvs values to be filled
    variant_df["g_hgvs"] = None

    # Rate limit: 4 requests per second (delay = 1/4 = 0.25 seconds)
    min_interval = 0.25

    for index, row in variant_df.iterrows():
        variant_desc = (
            f"{row['#CHROM']}-{row['POS']}-{row['REF']}-{row['ALT']}"
        )

        start_time = time.time()
        vv_response = call_variant_validator(variant_desc)[variant_desc][
            variant_desc
        ]

        if vv_response["genomic_variant_error"] is None:
            g_hgvs = vv_response["g_hgvs"]
            variant_df.at[index, "g_hgvs"] = g_hgvs

        else:
            logger.warning(
                f"Variant {variant_desc} could not be validated: "
                f"{vv_response['genomic_variant_error']}"
            )

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
    validated_df.to_csv("output.csv")

if __name__ == "__main__":
    main()