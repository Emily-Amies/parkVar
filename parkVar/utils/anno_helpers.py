from flask import Flask, request, render_template_string, flash, redirect, url_for
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from parkVar.utils.logger_config import logger
from parkVar.utils import anno_helpers as anno
from parkVar.modules.validate import validate_variants
from parkVar.modules.clinvar_annotator import process_variants_file

def _validate(input_path, validator_path):

    try:
        # Creates validated_data.csv in data/
        validate_variants(input_path, validator_path)
    except Exception as e:
        raise flask_utils.ProcessError(
            context = 'Validation',
            original_exception=e
    )
    # Double check validation step completed
    if not validator_path.exists():
        raise flask_utils.MissingFileError(
            context='validated_data.csv',
            original_exception=FileNotFoundError(f'{context} does not exist')
        )
        
def _annotate(validator_path, anno_path):

    try:
        # Creates anno_data.csv in data/
        process_variants_file(validator_path)
    except Exception as e:
        raise flask_utils.ProcessError(
            context = 'Annotation',
            original_exception=e
    )

    # Double check annotation step completed
    if not anno_path.exists():
        raise flask_utils.MissingFileError(
            context='anno_data.csv',
            original_exception=FileNotFoundError(f'{context} does not exist')
        )

def _build_table(anno_path):

    # Read csv to pandas dataframe
    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        raise flask_utils.CSVReadError(
            context = 'anno_data.csv',
            original_exception=e
    )

    logger.info(f'Loaded annotated data with {len(df)} rows')

    # build HTML table
    table_html = flask_utils.create_table(df)

    return df, table_html