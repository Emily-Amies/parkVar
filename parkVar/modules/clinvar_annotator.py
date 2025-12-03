import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from requests import RequestException

from parkVar.utils.logger_config import logger

# Step 1: Define constants for ClinVar API

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


# Step 2: Query ClinVar API using defined parameters and rate limiting


class ClinVarClient:
    """
    ClinVar API client to return uid for input HGVS, and then fetch esummary
    for each uid. Definded as a class for implementing testing.
    """

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        rate_limit_sleep: float = NCBI_RATE_LIMIT_SLEEP,
    ):
        """
        Initiate the API client.

        Parameters
        ----------
        session : requests.Session or None
            Start requests session or generate new session
            to use for HTTP calls, incorporating rate limiting.
        rate_limit_sleep : float
            Seconds between requests for NCBI rate limit.
        """

        self.session = session or requests.Session()
        self.rate_limit_sleep = rate_limit_sleep

    def _get_json(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a GET request and return in JSON format.

        Parameters
        ----------
        url : str
            ClinVar URL for GET.
        params : dict
            Query parameters for the request.

        Returns
        -------
        JSON : dict
            Returned JSON.

        Raises
        ------
        requests.HTTPError
            If error returned then: status code not 200.
        requests.RequestException
            For non-200 status errors.
        """
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except RequestException as exc:
            logger.error(
                "HTTP request failed: url=%s params=%s error=%s",
                url,
                params,
                exc,
                exc_info=True,
            )
            # log error but re-raise for caller to handle
            raise

    def search_hgvs(self, hgvs: str) -> List[str]:
        """
        Search ClinVar for a given HGVS string and return matching UIDs.

        Parameters
        ----------
        hgvs : str
            HGVS variant string to search from validate.py

        Returns
        -------
        uids : list
            List of matching ClinVar UIDs (may be empty if no match/error).
        """

        url = f"{EUTILS_BASE}/esearch.fcgi"
        params = {"db": "clinvar", "term": hgvs, "retmode": "json"}
        try:
            data = self._get_json(url, params)
            uids = data.get("esearchresult", {}).get("idlist", [])
        except Exception as exc:
            logger.error(
                "Failed to search ClinVar for %s: %s", hgvs, exc, exc_info=True
            )
            return []  # return empty list on fail (logged)
        time.sleep(self.rate_limit_sleep)
        return uids

    def fetch_esummary(self, uid: str) -> Dict[str, Any]:
        """
        Fetch esummary entry for ClinVar UIDs.

        Parameters
        ----------
        uid : str
            ClinVar UID to fetch.

        Returns
        -------
        esum : dict
            The esummary dictionary for the UID. If the UID returns nothing,
            or and error occurs, an empty dict is returned
        """

        url = f"{EUTILS_BASE}/esummary.fcgi"
        params = {"db": "clinvar", "id": uid, "retmode": "json"}
        try:
            data = self._get_json(url, params)
            esum = data.get("result", {}).get(uid, {}) or {}
        except Exception as exc:
            logger.error(
                "Failed to fetch esummary for UID %s: %s",
                uid,
                exc,
                exc_info=True,
            )
            return {}
        time.sleep(self.rate_limit_sleep)
        return esum

    def extract_disease_from_trait_set(
        clin_sig: Dict[str, Any],
    ) -> Dict[str, Optional[str]]:
        """
        Extract disease name and OMIM ID from ClinVar trait values.

        Parameters
        ----------
        clin_sig : dict
            A ClinVar clinical significance or classification dictionary
            containing 'trait_set' or 'traits' from esum.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'disease_name' (str or None): The disease name.
            - 'disease_mim' (str or None): The OMIM ID.
        """

        disease_name = None
        disease_mim = None

        if not isinstance(clin_sig, dict):
            return {"disease_name": None, "disease_mim": None}

        trait_set = clin_sig.get("trait_set") or clin_sig.get("traits") or []
        if isinstance(trait_set, list) and trait_set:
            first_trait = (
                trait_set[0] if isinstance(trait_set[0], dict) else {}
            )
            disease_name = first_trait.get("trait_name") or first_trait.get(
                "name"
            )
            xrefs = (
                first_trait.get("trait_xrefs")
                or first_trait.get("xrefs")
                or []
            )
            for xref in xrefs:
                if not isinstance(xref, dict):
                    continue
                db_source = (
                    xref.get("db_source") or xref.get("db") or ""
                ).upper()
                if db_source == "OMIM":
                    disease_mim = xref.get("db_id") or xref.get("id")
                    break

        return {"disease_name": disease_name, "disease_mim": disease_mim}

    def extract_consensus_and_stars(
        esummary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract classification information and map to star rating.

        Parameters
        ----------
        esummary : dict
            The esummary dictionary as returned by ClinVar API.

        Returns
        -------
        dict
            Dictionary with keys:
            - 'classification' (str or None): Classification description.
            - 'review_status_text' (str or None): Review status from esummary.
            - 'star_rating' (int or None): Star rating (0-4).
            - 'disease_name' (str or None): Extracted disease name.
            - 'disease_mim' (str or None): Extracted OMIM identifier.
        """

        clin_sig = {}
        if isinstance(esummary, dict):
            clin_sig = (
                esummary.get("germline_classification")
                or esummary.get("clinical_significance")
                or {}
            )

        classification = clin_sig.get("description")
        review_status_text = clin_sig.get("review_status")
        star_rating: Optional[int] = None

        if isinstance(review_status_text, str):
            normalized = review_status_text.strip().lower()
            if normalized in REVIEW_STATUS_TO_STARS:
                star_rating = REVIEW_STATUS_TO_STARS[normalized]
            else:
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
                    star_rating = None

        disease_info = ClinVarClient.extract_disease_from_trait_set(clin_sig)
        return {
            "classification": classification,
            "review_status_text": review_status_text,
            "star_rating": star_rating,
            "disease_name": disease_info.get("disease_name"),
            "disease_mim": disease_info.get("disease_mim"),
        }


# Step 3: Annotate DataFrame with ClinVar data


def annotate_dataframe(
    df: pd.DataFrame, client: ClinVarClient
) -> pd.DataFrame:
    """
    Annotate a DataFrame of variants with ClinVar information.

    Parameters
    ----------
    df : pandas.DataFrame
        Input dataframe that must contain a 't_hgvs' column with HGVS strings.
    client : ClinVarClient
        ClinVarClient for retrieving summaries.

    Returns
    -------
    pandas.DataFrame
        Input DataFrame with updated columns:
        'clinvar_uid', 'classification', 'review_status_text', 'star_rating',
        'disease_name', 'disease_mim'.

    Raises
    ------
    KeyError
        If the input DataFrame does not contain a 't_hgvs' column.
    ValueError
        If the input DataFrame is empty.
    """
    if "t_hgvs" not in df.columns:
        logger.error("DataFrame missing required column 't_hgvs'")
        raise KeyError("Input DataFrame must contain 't_hgvs' column")

    if df.empty:
        logger.error("Input DataFrame is empty")
        raise ValueError("No variants to annotate")

    out = df.copy()
    for col in [
        "clinvar_uid",
        "classification",
        "review_status_text",
        "star_rating",
        "disease_name",
        "disease_mim",
    ]:
        if col not in out.columns:
            out[col] = None

    for idx, row in out.iterrows():
        hgvs_input = row["t_hgvs"]
        logger.info("Processing variant: %s", hgvs_input)
        try:
            uids = client.search_hgvs(hgvs_input)
            if not uids:
                logger.debug("No ClinVar UID found for %s", hgvs_input)
                continue
            uid = uids[0]
            logger.debug("Using ClinVar UID %s for %s", uid, hgvs_input)
            esummary = client.fetch_esummary(uid)
            extracted = client.extract_consensus_and_stars(esummary)

            out.at[idx, "clinvar_uid"] = uid
            out.at[idx, "classification"] = extracted["classification"]
            out.at[idx, "review_status_text"] = extracted["review_status_text"]
            out.at[idx, "star_rating"] = extracted["star_rating"]
            out.at[idx, "disease_name"] = extracted["disease_name"]
            out.at[idx, "disease_mim"] = extracted["disease_mim"]

        except Exception as exc:
            logger.warning(
                "Error annotating %s: %s", hgvs_input, exc, exc_info=True
            )
            continue

    return out


# Step 4: Main function to process input CSV and write output CSV


def process_variants_file(
    input_csv: Path,
    client: Optional[ClinVarClient] = None,
    output_name: str = "anno_data.csv",
) -> Path:
    """
    Read variant CSV, annotate using ClinVar, and write to output CSV.

    Parameters
    ----------
    input_csv : pathlib.Path
        Path to the input CSV file to read.
    client : ClinVarClient or None, optional
        ClinVarClient for annotation. If none, client is created.
    output_name : str, optional
        Output CSV file written to the same directory as input_csv.

    Returns
    -------
    pathlib.Path
        Path to the written annotated CSV file.

    Raises
    ------
    Exception
        If reading the input CSV fails, an exception with context is raised.
    """
    client = client or ClinVarClient()
    try:
        df = pd.read_csv(input_csv)
    except Exception as e:
        logger.error(
            "Failed to read input CSV %s: %s", input_csv, e, exc_info=True
        )
        raise

    annotated = annotate_dataframe(df, client)

    output_csv = input_csv.parent / output_name
    try:
        annotated.to_csv(output_csv, index=False)
        logger.info("Annotations written to %s", output_csv)
    except Exception as e:
        logger.error(
            "Failed to write annotated CSV %s: %s",
            output_csv,
            e,
            exc_info=True,
        )
        raise
    return output_csv
