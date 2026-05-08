import pytest
from pydantic import ValidationError

from src.phase2.preferences import UserPreferences


def test_user_preferences_normalization() -> None:
    payload = {
        "location": "Bengaluru",
        "budget": "Medium",
        "cuisines": "North Indian, Chinese",
        "minimum_rating": 4.2,
        "additional_preferences": "Family-friendly, Quick Service",
    }
    preferences = UserPreferences.model_validate(payload)
    assert preferences.location == "bangalore"
    assert preferences.budget == "medium"
    assert preferences.cuisines == ["chinese", "north indian"]


def test_user_preferences_rejects_invalid_budget() -> None:
    with pytest.raises(ValidationError):
        UserPreferences.model_validate(
            {
                "location": "Delhi",
                "budget": "premium",
                "cuisines": ["north indian"],
                "minimum_rating": 4.0,
            }
        )
