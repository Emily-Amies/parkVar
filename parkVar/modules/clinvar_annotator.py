import csv
import time
from typing import Optional

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


def extract_consensus_and_stars(esummary: dict) -> dict:
    """
    Extract consensus classification, review status text and star rating.

    Parameters
    ----------
    esummary : dict
        ClinVar esummary dictionary (as returned by fetch_esummary_for_uid).

    Returns
    -------
    dict
        Dictionary with keys:
        - consensus_classification (str or None): textual consensus
        classification
          (e.g., "Pathogenic", "Likely pathogenic", "Conflicting
          interpretations of pathogenicity").
        - review_status_text (str or None): raw review status text from the
        esummary.
        - star_rating (int or None): deduced star rating (0-4) where available,
          otherwise None.
    """
    # germline_classification dict from esummary
    clin_sig = (
        esummary.get("germline_classification", {})
        if isinstance(esummary, dict)
        else {}
    )
    # Textual consensus classification (e.g., "Pathogenic", "Likely
    # pathogenic", "Conflicting interpretations of pathogenicity")
    consensus_classification = clin_sig.get("description")
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
                # Unknown / new textual form — set to None (caller can treat as
                #  unknown)
                star_rating = None

    # Return a small dict containing the extracted fields
    return {
        "consensus_classification": consensus_classification,
        "review_status_text": review_status_text,
        "star_rating": star_rating,
    }


# Main script logic

if __name__ == "__main__":
    # Input HGVS:

    hgvs_input = "NM_001377265.1:c.841G>T"

    # Find ClinVar UIDs for the HGVS
    try:
        # Call helper that wraps esearch; returns list of UID strings (may be
        #  empty)
        uids = find_clinvar_uids_for_hgvs(hgvs_input)
    except Exception as exc:
        # If the HTTP request or parsing fails, print an error and exit
        print(
            f"ERROR: Failed to search "
            f"ClinVar for HGVS '{hgvs_input}': {exc}"
        )
        raise

    # Delay for NCBI rate limiting
    time.sleep(NCBI_RATE_LIMIT_SLEEP)

    # Report found UIDs
    if not uids:
        # No ClinVar records found for the HGVS expression
        print("No ClinVar UID found for that HGVS.")
        # Still write an empty CSV row to indicate no result (optional)
        with open("clinvar_result.csv", "w", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "hgvs",
                    "clinvar_uid",
                    "consensus_classification",
                    "review_status_text",
                    "star_rating",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "hgvs": hgvs_input,
                    "clinvar_uid": None,
                    "consensus_classification": None,
                    "review_status_text": None,
                    "star_rating": None,
                }
            )
        # Exit the script (nothing else to fetch)
        raise SystemExit(0)
    else:
        # Use the top UID if multiple found (need to change later?)
        clinvar_uid = uids[0]
        print(f"Found ClinVar UID(s): {uids} -> using UID {clinvar_uid}")

    # Grab the esummary for the found UID
    try:
        # Fetch the ClinVar esummary JSON for the UID
        esummary = fetch_esummary_for_uid(clinvar_uid)
    except Exception as exc:
        # If fetching fails
        print(
            f"ERROR: Failed to fetch esummary for UID {clinvar_uid}: {exc}"
        )
        raise

    # Delay for NCBI rate limiting
    time.sleep(NCBI_RATE_LIMIT_SLEEP)

    # Pretty-print the desired fields from esummary
    print("Raw esummary keys available:", list(esummary.keys())[:20])

    # Extract desired fields
    extracted = extract_consensus_and_stars(esummary)

    # Print extracted values for user
    print("\nExtracted fields:")
    print(
        f"  consensus_classification: {extracted['consensus_classification']}"
    )
    print(f"  review_status_text:       {extracted['review_status_text']}")
    print(f"  star_rating (0-4):        {extracted['star_rating']}")

    # Write desired fields to CSV
    out_csv_path = "clinvar_hgvs_summary.csv"
    with open(out_csv_path, "w", newline="") as fh:
        # Define CSV column order
        fieldnames = [
            "hgvs",
            "clinvar_uid",
            "consensus_classification",
            "review_status_text",
            "star_rating",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        # Write header row
        writer.writeheader()
        # Write a single row with desired fields
        writer.writerow(
            {
                "hgvs": hgvs_input,
                "clinvar_uid": clinvar_uid,
                "consensus_classification": extracted[
                    "consensus_classification"
                ],
                "review_status_text": extracted["review_status_text"],
                "star_rating": extracted["star_rating"],
            }
        )

    # Final message
    print(f"\nDone — summary written to {out_csv_path}")
