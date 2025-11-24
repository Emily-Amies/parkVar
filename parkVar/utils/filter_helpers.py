from flask import Flask, request, render_template_string, flash, redirect, url_for
import pandas as pd
import io  # Needed for StringIO - used to make a file-like object in memory
from parkVar.utils import flask_utils
from pathlib import Path
from parkVar.utils.logger_config import logger

def _read_anno_data(anno_path):
    # Create pandas dataframe from csv
    try:
        df = pd.read_csv(anno_path)
    except Exception as e:
        raise flask_utils.CSVReadError(
            context = file.filename,
            original_exception=e
    )

    return df

def _filter_df(df, filtered_path):

    # Check if Patient_ID is in dataframe
    if 'Patient_ID' not in df.columns:
        raise flask_utils.MissingColumnError(
            context='Patient_ID',
            original_exception=KeyError('Patient_ID')
    )

    # List of selected patient IDs from the form
    selected_ids = request.form.getlist('patient_id')

    # Apply filter
    if selected_ids:
        filtered_df = df[df['Patient_ID'].astype(str).isin(selected_ids)]
        logger.info(f'Filter applied to Patient_ID(s): {selected_ids}')
        applied_text = f'Filtered by: {", ".join(selected_ids)}'
    else:
        # No boxes ticked = show everything
        filtered_df = df.copy()
        logger.info('No filter applied (no Patient_ID selected)')
        applied_text = 'No filter selected. Showing all rows.'

    # Write filtered data to CSV
    filtered_df.to_csv(filtered_path, index=False)

    return filtered_df, selected_ids, applied_text


def _show_filter_page(df, filtered_df, selected_ids, applied_text):

    # Rebuild checkbox values so the page can re-render them
    patient_ids = sorted(df['Patient_ID'].astype(str).dropna().unique().tolist())

    # Build the table HTML for the filtered frame
    table_html = flask_utils.create_table(filtered_df)

    return render_template_string(
        flask_utils.ANNO_TEMPLATE,
        applied_text=applied_text,
        table=table_html,
        patient_ids=patient_ids,
        selected_ids=selected_ids
    )