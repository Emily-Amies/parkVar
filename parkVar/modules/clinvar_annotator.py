import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# Defining constants etc

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_RATE_LIMIT_SLEEP = 0.34  # ~3 requests/sec as per NCBI

REVIEW_STATUS_TO_STARS = {
    "practice guideline": 4,
    "reviewed by expert panel": 3,
    "criteria provided, multiple submitters, no conflicts": 2,
    "criteria provided, single submitter": 1,
    "no assertion criteria provided": 0,
    "no classification provided": 0,
}

# ClinVar querying functions


def find_clinvar_uids_for_hgvs(hgvs: str) -> list:
    """
    Query ClinVar with an HGVS string and return associated UIDs.

    Parameters
    ----------
    hgvs : str
        HGVS expression to search for in the ClinVar database.

    Returns
    -------
    list
        List of UID strings found for the provided HGVS. May be empty if no
        matches.
    """
    # Define UID search url
    url = f"{EUTILS_BASE}/esearch.fcgi"
    # Define parameters: db=clinvar, term=HGVS, return JSON
    params = {"db": "clinvar", "term": hgvs, "retmode": "json"}
    # Perform HTTP GET request
    resp = requests.get(url, params=params, timeout=30)
    # Raise a Python exception for non-2xx
    resp.raise_for_status()
    # Parse the JSON to data
    data = resp.json()
    # Extract the list of UIDs
    uids = data.get("esearchresult", {}).get("idlist", [])
    # Return the list of UID strings
    return uids


def fetch_esummary_for_uid(uid: str) -> dict:
    """
    Fetch ClinVar esummary JSON for a given UID.

    Parameters
    ----------
    uid : str
        ClinVar UID to fetch the esummary for.

    Returns
    -------
    dict
        Parsed esummary dictionary corresponding to the requested UID. Empty
        dict if the UID is not present in the returned result payload.
    """
    # Define esummary URL
    url = f"{EUTILS_BASE}/esummary.fcgi"
    # Parameters: which database, which id, and what return mode
    params = {"db": "clinvar", "id": uid, "retmode": "json"}
    # GET request
    resp = requests.get(url, params=params, timeout=30)
    # Raise error status
    resp.raise_for_status()
    # Parse JSON into data
    data = resp.json()
    # Pull UID-specific esummary dict
    esum_for_uid = data.get("result", {}).get(uid, {})
    # Return the esummary dictionary for that UID
    return esum_for_uid


def extract_disease_from_trait_set(clin_sig: dict) -> dict:
    """
    Extract disease name and OMIM ID from ClinVar trait_set fields.

    Parameters
    ----------
    clin_sig : dict
        The classification from a ClinVar esummary (e.g.
        "germline_classification" or legacy "clinical_significance").
        This should contain a "trait_set" or "traits" field.

    Returns
    -------
    dict
        Dictionary with keys:
        - disease_name (str or None): name of the first disease
          (from "trait_name" or "name"), or None if not present.
        - disease_mim (str or None): OMIM ID (from "trait_xrefs"
          or "xrefs"), or None if not present.

    Notes
    -----
    Currently will only pull the first listed clinical indication for
    these fields.
    """
    disease_name = None
    disease_mim = None

    if not isinstance(clin_sig, dict):
        return {"disease_name": None, "disease_mim": None}

    trait_set = clin_sig.get("trait_set") or clin_sig.get("traits") or []
    if isinstance(trait_set, list) and trait_set:
        first_trait = trait_set[0] if isinstance(trait_set[0], dict) else {}
        # "disease name" could be in trait_name or name
        disease_name = first_trait.get("trait_name") or first_trait.get("name")
        # "xrefs" could be either in trait_xrefs or xrefs
        xrefs = first_trait.get("trait_xrefs") or first_trait.get("xrefs") or [
        ]
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            db_source = (xref.get("db_source") or xref.get("db") or "").upper()
            if db_source == "OMIM":
                disease_mim = xref.get("db_id") or xref.get("id")
                break

    return {"disease_name": disease_name, "disease_mim": disease_mim}


def extract_consensus_and_stars(esummary: dict) -> dict:
    """
    Extract consensus classification, review status, star rating,
    disease name and MIM ID.

    Parameters
    ----------
    esummary : dict
        ClinVar esummary dictionary (as returned by fetch_esummary_for_uid).

    Returns
    -------
    dict
        Dictionary with keys:
        - classification (str or None):
        textual consensus classification
        - review_status_text (str or None): raw review status text
        - star_rating (int or None): deduced star rating (0-4)
        - disease_name (str or None): name of associated disease/condition
        - disease_mim (str or None): MIM ID of associated disease if available
    """
    # germline_classification dict from esummary
    # Fetch 'germline_classification' field; if missing
    # for legacy submissions, fall back to 'clinical_significance'.
    clin_sig = {}
    if isinstance(esummary, dict):
        clin_sig = esummary.get("germline_classification")
        if not clin_sig:
            clin_sig = esummary.get("clinical_significance", {})

    # Textual consensus classification (e.g., "Pathogenic", "Likely
    # pathogenic", "Conflicting interpretations of pathogenicity")
    classification = clin_sig.get("description")
    # The review_status text
    review_status_text = clin_sig.get("review_status")
    # Determine star rating from review_status_text
    star_rating: Optional[int] = None
    if isinstance(review_status_text, str):
        # Normalise whitespace and case to match keys in our mapping
        normalized = review_status_text.strip().lower()
        # If exact text maps to number of stars, use it
        if normalized in REVIEW_STATUS_TO_STARS:
            star_rating = REVIEW_STATUS_TO_STARS[normalized]
        else:
            # Some esummary review_status strings include commas or slight
            #  variations; attempt a best-effort match using substring
            # checks in order of precedence.
            if "practice guideline" in normalized:
                star_rating = 4
            elif "expert panel" in normalized:
                star_rating = 3
            elif (
                "multiple submitters" in normalized
                and "no conflicts" in normalized
            ):
                star_rating = 2
            elif (
                "criteria provided" in normalized
                and "single submitter" in normalized
            ):
                star_rating = 1
            elif (
                "no assertion criteria provided" in normalized
                or "no classification provided" in normalized
            ):
                star_rating = 0
            else:
                # Unknown review status text, then:
                star_rating = None

    # Extract disease information from trait_set using helper
    disease_info = extract_disease_from_trait_set(clin_sig)
    disease_name = disease_info.get("disease_name")
    disease_mim = disease_info.get("disease_mim")

    # Return dict with all extracted fields
    return {
        "classification": classification,
        "review_status_text": review_status_text,
        "star_rating": star_rating,
        "disease_name": disease_name,
        "disease_mim": disease_mim,
    }


# Main script logic

def process_variants_file(input_csv: Path) -> Path:
    """
    Process validated_variants.csv and annotate with ClinVar data.

    Parameters
    ----------
    input_csv : Path
        Path to input CSV containing variants with 't_hgvs' column

    Returns
    -------
    Path
        Path to output CSV with ClinVar annotations added
    """
    # Read input CSV into DataFrame
    try:
        df = pd.read_csv(input_csv)
        if 't_hgvs' not in df.columns:
            raise KeyError("Input CSV must contain 't_hgvs' column")
    except Exception as e:
        raise Exception(f"Failed to read input CSV: {e}")

    if df.empty:
        raise ValueError("No variants found in input file")

    # Create new columns for ClinVar annotations
    clinvar_cols = {
        'clinvar_uid': None,
        'classification': None,
        'review_status_text': None,
        'star_rating': None,
        'disease_name': None,
        'disease_mim': None
    }
    for col in clinvar_cols:
        df[col] = None

    # Process each variant
    for idx, row in df.iterrows():
        hgvs_input = row['t_hgvs']
        print(f"\nProcessing variant: {hgvs_input}")

        try:
            uids = find_clinvar_uids_for_hgvs(hgvs_input)
            time.sleep(NCBI_RATE_LIMIT_SLEEP)

            if not uids:
                print(f"No ClinVar UID found for {hgvs_input}")
                continue

            clinvar_uid = uids[0]
            print(f"Found ClinVar UID(s): {uids} -> using {clinvar_uid}")

            esummary = fetch_esummary_for_uid(clinvar_uid)
            time.sleep(NCBI_RATE_LIMIT_SLEEP)

            extracted = extract_consensus_and_stars(esummary)

            # Update validated_variants dataframe with clinvar data
            df.at[idx, 'clinvar_uid'] = clinvar_uid
            df.at[idx, 'classification'] = extracted['classification']
            df.at[idx, 'review_status_text'] = extracted['review_status_text']
            df.at[idx, 'star_rating'] = extracted['star_rating']
            df.at[idx, 'disease_name'] = extracted['disease_name']
            df.at[idx, 'disease_mim'] = extracted['disease_mim']

        except Exception as exc:
            print(f"Error processing variant {hgvs_input}: {exc}")
            continue

    # Write appended dataframe to output CSV
    output_csv = input_csv.parent / "anno_data.csv"
    df.to_csv(output_csv, index=False)
    print(f"\nDone — annotations written to {output_csv}")

    return output_csv


# copilot splurge for running internally
if __name__ == "__main__":
    import sys
    from pathlib import Path

    if len(sys.argv) != 2:
        print("Usage: python clinvar_annotator.py <input_csv_path>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    try:
        process_variants_file(input_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
