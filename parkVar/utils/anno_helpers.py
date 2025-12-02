"""
Helpers for validating, annotating and rendering variant data tables.

This module provides thin wrappers around the core validation and
annotation functions so that they integrate cleanly with the Flask
error-handling layer.

Author: Emily Amies
Group: 4

Notes:
- Expects CSV files in the temporary 'data' directory.
- Raises custom Flask-aware exceptions defined in flask_utils.
"""

from pathlib import Path

import pandas as pd

from parkVar.utils import flask_utils
from parkVar.utils.logger_config import logger
from parkVar.modules.validate import validate_variants
from parkVar.modules.clinvar_annotator import process_variants_file

def _validate(input_path, validator_path):
    """
    Validate the input variant file and write a validated CSV.

    Parameters
    ----------
    input_path : pathlib.Path
        Path to the input CSV file containing raw variant data.
    validator_path : pathlib.Path
        Path where the validated CSV should be written.

    Raises
    ------
    flask_utils.MissingFileError
        If the input file does not exist.
    flask_utils.ProcessError
        If validation fails for any reason.
    """
    
    # Check input file exists
    if not input_path.exists():
        raise flask_utils.MissingFileError(
            context="input_data.csv",
            original_exception=FileNotFoundError(
                "input_data.csv does not exist"
            ),
        )

    try:
        # Creates validated_data.csv in data/
        validate_variants(input_path, validator_path)
    except Exception as e:
        raise flask_utils.ProcessError(
            context="Validation", original_exception=e
        )


def _annotate(validator_path):
    """
    Annotate validated variant data and write an annotated CSV.

    Parameters
    ----------
    validator_path : pathlib.Path
        Path to the validated CSV file (output of `_validate`).

    Raises
    ------
    flask_utils.MissingFileError
        If the validated file does not exist.
    flask_utils.ProcessError
        If annotation fails for any reason.
    """

    # Check validated_data.csv exists
    if not validator_path.exists():
        raise flask_utils.MissingFileError(
            context="validated_data.csv",
            original_exception=FileNotFoundError(
                "validated_data.csv does not exist"
            ),
        )

    try:
        # Creates anno_data.csv in data/
        process_variants_file(validator_path)
    except Exception as e:
        raise flask_utils.ProcessError(
            context="Annotation", original_exception=e
        )


def _build_table(anno_path):
    """
    Load an annotated CSV and build an HTML table.

    Parameters
    ----------
    anno_path : pathlib.Path
        Path to the annotated CSV file.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the annotated variant data.
    str
        HTML string representing the rendered table.

    Raises
    ------
    flask_utils.MissingFileError
        If the annotated file does not exist.
    flask_utils.CSVReadError
        If the CSV cannot be read into a DataFrame.
    """

    # Check validated_data.csv exists
    if not anno_path.exists():
        raise flask_utils.MissingFileError(
            context="anno_data.csv",
            original_exception=FileNotFoundError(
                "anno_data.csv does not exist"
            ),
        )

    # Read csv to pandas dataframe
    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        raise flask_utils.CSVReadError(
            context="anno_data.csv", original_exception=e
        )

    logger.info(f"Loaded annotated data with {len(df)} rows")

    # Build HTML table
    table_html = flask_utils.create_table(df)

    return df, table_html
