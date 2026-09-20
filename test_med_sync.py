import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

# Mock streamlit and supabase before importing the app module so the
# module-level UI code and Supabase client creation don't execute.
mock_st = MagicMock()
mock_st.session_state = {}
# st.tabs() must return an iterable with enough elements to unpack
mock_st.tabs.return_value = [MagicMock(), MagicMock()]
sys.modules['streamlit'] = mock_st
sys.modules['supabase'] = MagicMock()

from med_sync_app_final import calculate_sync_quantities  # noqa: E402


def _future_date(days=30):
    return (datetime.today() + timedelta(days=days)).strftime("%Y-%m-%d")


def _days_until(sync_date_str):
    return (datetime.strptime(sync_date_str, "%Y-%m-%d").date() - date.today()).days


def test_new_medication_units():
    """New medication should need daily_dose * days_until_sync units."""
    sync_date = _future_date(30)
    new_med = {'name': 'NewMed', 'daily_dose': 2}
    result = calculate_sync_quantities([], new_med, sync_date)

    assert len(result) == 1
    entry = result[0]
    assert entry['name'] == 'NewMed (new)'
    assert entry['days_left'] == 0
    assert entry['units_needed'] == new_med['daily_dose'] * _days_until(sync_date)


def test_existing_medication_enough_supply():
    """A medication with enough supply should need 0 additional units."""
    sync_date = _future_date(10)
    current_meds = [{'name': 'MedA', 'daily_dose': 1, 'remaining': 20}]
    new_med = {'name': 'NewMed', 'daily_dose': 1}
    result = calculate_sync_quantities(current_meds, new_med, sync_date)

    med_a = result[0]
    assert med_a['name'] == 'MedA'
    assert med_a['units_needed'] == 0


def test_existing_medication_insufficient_supply():
    """A medication with too little supply should need additional units."""
    sync_date = _future_date(30)
    current_meds = [{'name': 'MedB', 'daily_dose': 2, 'remaining': 10}]
    new_med = {'name': 'NewMed', 'daily_dose': 1}
    result = calculate_sync_quantities(current_meds, new_med, sync_date)

    med = current_meds[0]
    days_left = med['remaining'] // med['daily_dose']
    expected_units = (_days_until(sync_date) - days_left) * med['daily_dose']
    assert result[0]['units_needed'] == expected_units


def test_past_sync_date_returns_empty():
    """A sync date in the past should return an empty list."""
    past_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    new_med = {'name': 'NewMed', 'daily_dose': 1}
    result = calculate_sync_quantities([], new_med, past_date)
    assert result == []


def test_sync_date_today_returns_empty():
    """Today is not a valid sync date; nothing can be dispensed for zero days."""
    today = date.today().strftime("%Y-%m-%d")
    new_med = {'name': 'NewMed', 'daily_dose': 1}
    assert calculate_sync_quantities([], new_med, today) == []


def test_days_are_counted_as_whole_calendar_days():
    """Tomorrow is exactly one day away regardless of the current time of day."""
    tomorrow = _future_date(1)
    new_med = {'name': 'NewMed', 'daily_dose': 3}
    result = calculate_sync_quantities([], new_med, tomorrow)
    assert result[0]['units_needed'] == 3


def test_multiple_medications():
    """Multiple existing medications should all be included in the result."""
    sync_date = _future_date(20)
    current_meds = [
        {'name': 'Med1', 'daily_dose': 1, 'remaining': 5},
        {'name': 'Med2', 'daily_dose': 3, 'remaining': 30},
    ]
    new_med = {'name': 'NewMed', 'daily_dose': 2}
    result = calculate_sync_quantities(current_meds, new_med, sync_date)

    assert len(result) == 3
    names = [r['name'] for r in result]
    assert 'Med1' in names
    assert 'Med2' in names
    assert 'NewMed (new)' in names
