from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from requests import RequestException

import parkVar.modules.clinvar_annotator as annotate


@pytest.fixture
def sample_esummary():
    """Fixture to provide a sample esummary response from ClinVar."""
    return {
        "germline_classification": {
            "description": "Pathogenic",
            "review_status": "practice guideline",
            "trait_set": [
                {
                    "trait_name": "Example Disease",
                    "trait_xrefs": [
                        {"db_source": "OMIM", "db_id": "123456"}
                    ],
                }
            ],
        }
    }

def test_extract_disease_from_trait_set_basic():
    clin_sig = {
        "trait_set": [
            {
                "trait_name": "Test Disease",
                "trait_xrefs": [{"db_source": "OMIM", "db_id": "654321"}],
            }
        ]
    }
    res = annotate.ClinVarClient.extract_disease_from_trait_set(clin_sig)
    assert res["disease_name"] == "Test Disease"
    assert res["disease_mim"] == "654321"

@pytest.mark.parametrize(
    "review_text,expected_stars",
    [
        ("practice guideline", 4),
        ("reviewed by expert panel", 3),
        ("criteria provided, multiple submitters, no conflicts", 2),
        ("criteria provided, single submitter", 1),
        ("no assertion criteria provided", 0),
    ],
)
def test_extract_consensus_and_stars_mappings(review_text, expected_stars):
    esummary = {
        "germline_classification": {"description": "X",
                                     "review_status": review_text}
    }
    out = annotate.ClinVarClient.extract_consensus_and_stars(esummary)
    assert out["classification"] == "X"
    assert out["star_rating"] == expected_stars


def test_annotate_dataframe_with_mock_client(sample_esummary):
    df = pd.DataFrame({"t_hgvs": ["NM_1:c.1A>T", "NM_2:c.2G>C"]})
    mock_client = MagicMock(spec=annotate.ClinVarClient)
    # return a UID for first HGVS, not for second
    mock_client.search_hgvs.side_effect = [["11111"], []]
    mock_client.fetch_esummary.return_value = sample_esummary
    # use clinsig extractor method from client
    mock_client.extract_consensus_and_stars = (
        annotate.ClinVarClient.extract_consensus_and_stars)

    out = annotate.annotate_dataframe(df, mock_client)
    # first row should be annotated
    assert out.loc[0, "clinvar_uid"] == "11111"
    assert out.loc[0, "classification"] == "Pathogenic"
    assert out.loc[0, "star_rating"] == 4
    assert out.loc[0, "disease_name"] == "Example Disease"
    assert out.loc[0, "disease_mim"] == "123456"
    # second row should remain emtpy as no uid
    assert {pd.isna(out.loc[1, "clinvar_uid"])
             or out.loc[1, "clinvar_uid"] is None}


def test_annotate_dataframe_missing_column_logs_and_raises(caplog):
    df = pd.DataFrame({"not_hgvs": ["x"]})
    with pytest.raises(KeyError):
        annotate.annotate_dataframe(df, MagicMock(spec=annotate.ClinVarClient))
    # logger should have error entry about missing column
    assert any("t_hgvs" in rec.getMessage() for rec in caplog.records)


def test_process_variants_file_reads_and_writes(tmp_path, sample_esummary):
    # prepare input CSV
    in_csv = tmp_path / "input.csv"
    df = pd.DataFrame({"t_hgvs": ["NM_1:c.1A>T"]})
    df.to_csv(in_csv, index=False)

    # mock client
    mock_client = MagicMock(spec=annotate.ClinVarClient)
    mock_client.search_hgvs.return_value = ["22222"]
    mock_client.fetch_esummary.return_value = sample_esummary
    mock_client.extract_consensus_and_stars = (
        annotate.ClinVarClient.extract_consensus_and_stars)

    out_path = annotate.process_variants_file(
        in_csv, client=mock_client, output_name="out.csv")
    assert out_path.exists()
    out_df = pd.read_csv(out_path)
    assert "clinvar_uid" in out_df.columns
    assert str(out_df.loc[0, "clinvar_uid"]) == "22222"


def test_search_hgvs_returns_empty_on_exception_and_logs(caplog):
    client = annotate.ClinVarClient(session=MagicMock())
    # force _get_json to raise RequestException
    with patch.object(annotate.ClinVarClient, "_get_json",
                       side_effect=RequestException("oops")):
        res = client.search_hgvs("NM_1:c.1A>T")
    assert res == []
    assert any("Failed to search ClinVar" in
                rec.getMessage() for rec in caplog.records)
