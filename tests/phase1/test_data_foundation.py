import pandas as pd

from src.phase1.data_foundation import _standardize_schema


def test_standardize_schema_maps_and_filters_rows() -> None:
    raw = pd.DataFrame(
        [
            {
                "name": "A2B",
                "location": "Bengaluru",
                "cuisines": "North Indian, Chinese",
                "rate": "4.3/5",
                "approx_cost(for two people)": "600",
            },
            {
                "name": "",
                "location": "Delhi",
                "cuisines": "North Indian",
                "rate": "NEW",
                "approx_cost(for two people)": "400",
            },
        ]
    )

    result = _standardize_schema(raw)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["restaurant_name"] == "A2B"
    assert row["location"] == "bangalore"
    assert row["budget_bucket"] == "medium"
