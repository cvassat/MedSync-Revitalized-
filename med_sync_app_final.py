import logging
import os
from datetime import date, datetime

import streamlit as st
from supabase import Client, create_client

logger = logging.getLogger(__name__)

# Public anon key for the shared MedSync7 project. It is safe to publish
# because every table is protected by row-level security, but a deployment
# should still point at its own project via SUPABASE_URL / SUPABASE_KEY
# (environment variables or .streamlit/secrets.toml).
DEFAULT_SUPABASE_URL = "https://slwbhftsdffvsiazhrjg.supabase.co"
DEFAULT_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNsd2JoZnRzZGZmdnNpYXpocmpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDc2Nzc3NzQs"
    "ImV4cCI6MjA2MzI1Mzc3NH0."
    "wScgpTbOkRj-Bz-V7IWNvOHBdt_eZ3kpQTr9UGhgz_k"
)


def _setting(name, default):
    """Resolve a setting from the environment, then st.secrets, then a default."""
    value = os.environ.get(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
    except Exception:  # no secrets file, or secrets unavailable in this context
        value = None
    if isinstance(value, str) and value:
        return value
    return default


SUPABASE_URL = _setting("SUPABASE_URL", DEFAULT_SUPABASE_URL)
SUPABASE_KEY = _setting("SUPABASE_KEY", DEFAULT_SUPABASE_KEY)
USING_DEFAULT_SUPABASE = (
    SUPABASE_URL == DEFAULT_SUPABASE_URL and SUPABASE_KEY == DEFAULT_SUPABASE_KEY
)

if USING_DEFAULT_SUPABASE:
    logger.warning(
        "SUPABASE_URL / SUPABASE_KEY not set; using the default shared project. "
        "Set them in the environment or .streamlit/secrets.toml for your own deployment."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def _clean_text(value):
    return value.strip() if isinstance(value, str) else ""


def _is_positive_int(value):
    return isinstance(value, int) and value > 0


def _parse_sync_date(sync_date):
    if isinstance(sync_date, date):
        return sync_date
    if not isinstance(sync_date, str):
        return None
    try:
        return datetime.strptime(sync_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def _validate_sync_inputs(current_meds, new_med, sync_date):
    parsed_sync_date = _parse_sync_date(sync_date)
    if not parsed_sync_date:
        return None, "Sync date must use YYYY-MM-DD."

    days_until_sync = (parsed_sync_date - date.today()).days
    if days_until_sync <= 0:
        return None, "Sync date must be after today."

    for med in current_meds:
        if not _clean_text(med.get('name')):
            return None, "Every existing medication needs a name."
        if not _is_positive_int(med.get('daily_dose')):
            return None, f"Daily dose for {med.get('name', 'a medication')} must be a whole number above zero."
        if not isinstance(med.get('remaining'), int) or med['remaining'] < 0:
            return None, f"Remaining units for {med.get('name', 'a medication')} cannot be negative."

    if not _clean_text(new_med.get('name')):
        return None, "New medication needs a name."
    if not _is_positive_int(new_med.get('daily_dose')):
        return None, "New medication daily dose must be a whole number above zero."

    return parsed_sync_date, ""


def show_login():
    st.title("Login to Medication Sync App")
    if USING_DEFAULT_SUPABASE:
        st.caption("Connected to the default shared Supabase project.")
    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with login_tab:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            email = _clean_text(email)
            if not email or not password:
                st.error("Email and password are required.")
                return
            try:
                user = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if user:
                    st.session_state['user'] = user
                    st.success("Logged in successfully!")
            except Exception as e:
                logger.exception("Login failed for provided credentials: %s", e)
                st.error("Login failed. Please verify your credentials and try again.")

    with signup_tab:
        new_email = st.text_input("New Email", key="signup_email")
        new_password = st.text_input("New Password", type="password", key="signup_password")
        if st.button("Sign Up"):
            new_email = _clean_text(new_email)
            if not new_email or not new_password:
                st.error("Email and password are required.")
                return
            if len(new_password) < 8:
                st.error("Password must be at least 8 characters.")
                return
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_password})
                st.success("Sign-up successful! Please check your email to confirm.")
            except Exception as e:
                logger.exception("Sign-up failed for provided email: %s", e)
                st.error("Sign-up failed. Please try again later.")


def calculate_sync_quantities(current_meds, new_med, sync_date):
    validated_sync_date, validation_message = _validate_sync_inputs(current_meds, new_med, sync_date)
    if not validated_sync_date:
        st.error(validation_message)
        return []

    results = []
    days_until_sync = (validated_sync_date - date.today()).days

    for med in current_meds:
        days_left = med['remaining'] // med['daily_dose']
        additional_days_needed = days_until_sync - days_left
        units_needed = max(additional_days_needed * med['daily_dose'], 0)
        results.append({
            'name': _clean_text(med['name']),
            'days_left': days_left,
            'units_needed': units_needed
        })

    new_med_units = new_med['daily_dose'] * days_until_sync
    results.append({
        'name': _clean_text(new_med['name']) + " (new)",
        'days_left': 0,
        'units_needed': new_med_units
    })

    return results


if 'user' not in st.session_state:
    show_login()
else:
    st.title("Medication Sync Calculator")
    if st.sidebar.button("Logout"):
        st.session_state.pop('user', None)
        st.rerun()
    st.write("Calculate how many units are needed to align all medications, including a new one, to the same refill date.")

    with st.form("med_form"):
        num_meds = st.number_input("Number of existing medications", min_value=0, max_value=10, step=1, format="%d")
        meds = []
        for i in range(int(num_meds)):
            name = st.text_input(f"Medication {i+1} Name", key=f"name_{i}")
            daily_dose = st.number_input(f"Daily Dose for Medication {i+1}", min_value=1, key=f"dose_{i}", format="%d")
            remaining = st.number_input(f"Units Remaining for Medication {i+1}", min_value=0, key=f"remaining_{i}", format="%d")
            meds.append({'name': name, 'daily_dose': int(daily_dose), 'remaining': int(remaining)})

        st.markdown("### New Medication Details")
        new_name = st.text_input("New Medication Name", key="new_name")
        new_dose = st.number_input("New Medication Daily Dose", min_value=1, key="new_dose", format="%d")
        new_med = {'name': new_name, 'daily_dose': int(new_dose)}

        sync_date = st.date_input("Desired Sync Date")
        submitted = st.form_submit_button("Calculate")

    if submitted:
        result = calculate_sync_quantities(meds, new_med, sync_date.strftime("%Y-%m-%d"))
        if result:
            st.subheader("Sync Plan")
            for med in result:
                st.write(f"**{med['name']}**: {med['units_needed']} units needed to sync by {sync_date}")
