import streamlit as st
import re
from datetime import datetime

DL_PATTERN = re.compile(
    r"^DL-(DHK|CTG|SYL|RJH|KHL|BAR|RNG|MYM|GOV|PDB|STN)-\d{4}-\d{4}$"
)

def is_valid_email(email: str) -> bool:
    pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email.strip()))

def is_valid_dl(dl: str) -> bool:
    return bool(DL_PATTERN.match(dl.strip().upper()))

def is_valid_password(password: str) -> tuple:

    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number."
    if " " in password:
        return False, "Password cannot contain spaces."
    return True, ""

def is_valid_name(name: str) -> tuple:

    name = name.strip()
    if len(name) < 3:
        return False, "Name must be at least 3 characters."
    if len(name) > 100:
        return False, "Name cannot exceed 100 characters."
    if not re.match(r"^[A-Za-z\u0980-\u09FF\s\-'\.]+$", name):
        return False, "Name can only contain letters, spaces, hyphens and apostrophes."
    words = [w for w in name.split() if w]
    if len(words) < 2:
        return False, "Please enter your full name (first and last name)."
    return True, ""


def register_user(db, full_name: str, email: str,
                  driver_license: str, password: str,
                  confirm_password: str) -> dict:
    if not full_name or not full_name.strip():
        return {"success": False, "message": "Please enter your full name."}
    if not email or not email.strip():
        return {"success": False, "message": "Please enter your email address."}
    if not driver_license or not driver_license.strip():
        return {"success": False, "message": "Please enter your driver's license number."}
    if not password:
        return {"success": False, "message": "Please enter a password."}
    if not confirm_password:
        return {"success": False, "message": "Please confirm your password."}


    valid, msg = is_valid_name(full_name)
    if not valid:
        return {"success": False, "message": msg}


    if not is_valid_email(email):
        return {"success": False,
                "message": "Please enter a valid email address."}


    dl_clean = driver_license.strip().upper()
    if not is_valid_dl(dl_clean):
        return {"success": False,
                "message": (
                    "Driver's license format is invalid. "
                    "Expected format: DL-DHK-2341-2021"
                )}


    valid, msg = is_valid_password(password)
    if not valid:
        return {"success": False, "message": msg}

    if password != confirm_password:
        return {"success": False, "message": "Passwords do not match."}


    existing_email = db.get_user_by_email(email.strip().lower())
    if existing_email:
        return {"success": False,
                "message": "This email is already registered. Please log in instead."}

    existing_dl = db.get_user_by_dl(dl_clean)
    if existing_dl:
        return {"success": False,
                "message": (
                    "This driver's license is already associated with "
                    "an account. Please log in instead."
                )}


    try:
        user_id = db.create_user(
            full_name.strip(),
            email.strip().lower(),
            password,
            dl_clean
        )
    except Exception as e:
        return {"success": False,
                "message": f"Registration failed. Please try again."}

    return {
        "success":       True,
        "user_id":       user_id,
        "role":          "user",
        "user_name":     full_name.strip(),
        "driver_license": dl_clean,
        "email":         email.strip().lower(),
        "station_id":    None,
        "assigned_city": None,
        "force_pw_change": False,
    }


def login_user(db, identifier: str, password: str) -> dict:

    if not identifier or not identifier.strip():
        return {"success": False, "message": "Please enter your email or driver's license."}
    if not password:
        return {"success": False, "message": "Please enter your password."}

    identifier = identifier.strip()


    user = db.get_user_by_email(identifier.lower())
    if not user:
        user = db.get_user_by_dl(identifier.upper())

    if not user:

        return {"success": False,
                "message": "Invalid credentials. Please check and try again."}


    if not db.verify_password(password, user["password_hash"]):
        return {"success": False,
                "message": "Invalid credentials. Please check and try again."}

    return {
        "success":        True,
        "user_id":        user["id"],
        "role":           user["role"],
        "user_name":      user["full_name"],
        "driver_license": user["driver_license"],
        "email":          user["email"],
        "station_id":     user["station_id"],
        "assigned_city":  user["assigned_city"],
        "force_pw_change": bool(user["force_password_change"]),
    }


def logout_user():
    auth_keys = [
        "logged_in", "role", "user_id", "user_name",
        "driver_license", "email", "station_id",
        "assigned_city", "force_pw_change", "govt_view",
        "slot_hold", "slot_hold_until",
        "booking_step", "selected_city", "selected_area",
        "selected_station", "selected_vehicle",
        "selected_fuel", "requested_amount", "selected_slot",
        "fuel_view",
    ]
    for key in auth_keys:
        if key in st.session_state:
            del st.session_state[key]


    st.session_state.logged_in    = False
    st.session_state.role         = None
    st.session_state.user_id      = None
    st.session_state.user_name    = None
    st.session_state.driver_license = None
    st.session_state.email        = None
    st.session_state.station_id   = None
    st.session_state.assigned_city = None
    st.session_state.force_pw_change = False
    st.session_state.govt_view    = None


def require_role(*allowed_roles):
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_role = st.session_state.get("role")
            if current_role not in allowed_roles:
                st.error("🚫 Access denied. You do not have permission to view this page.")
                st.stop()
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__  = func.__doc__
        return wrapper
    return decorator

def get_active_suspension_message(db, driver_license: str) -> str | None:
    if not driver_license:
        return None

    suspension = db.get_active_suspension(driver_license)
    if not suspension:
        return None


    try:
        until_dt = datetime.strptime(
            suspension["suspended_until"], "%Y-%m-%d %H:%M:%S"
        )
        until_str = until_dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        until_str = suspension["suspended_until"]

    reason = suspension["reason"]
    return (
        f"Your booking access is restricted until {until_str}. "
        f"Reason: {reason}"
    )


def check_late_cancellation(db, driver_license: str,
                             slot_datetime_str: str) -> dict:
    if not slot_datetime_str:
        return {"tier": "clean", "message": "", "hours": 0}

    try:
        slot_dt = datetime.strptime(slot_datetime_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return {"tier": "clean", "message": "", "hours": 0}

    now            = datetime.now()
    hours_before   = (slot_dt - now).total_seconds() / 3600


    if hours_before >= 2:
        return {
            "tier":    "clean",
            "message": "Your booking will be cancelled. No penalty applies.",
            "hours":   0
        }


    month_year = now.strftime("%Y-%m")


    c = db.conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM suspensions
        WHERE driver_license=?
        AND suspension_type='late_cancellation'
        AND strftime('%Y-%m', suspended_at) = ?
    """, (driver_license, month_year))
    cancel_count = c.fetchone()[0]

    if cancel_count == 0:

        return {
            "tier":    "ban_24",
            "message": (
                "⚠️ You are cancelling less than 2 hours before your appointment. "
                "A 24-hour booking restriction will be applied to your account."
            ),
            "hours":   24
        }
    elif cancel_count == 1:

        return {
            "tier":    "ban_72",
            "message": (
                "⚠️ You are cancelling less than 2 hours before your appointment. "
                "This is your second late cancellation this month. "
                "A 72-hour booking restriction will be applied."
            ),
            "hours":   72
        }
    else:

        return {
            "tier":    "ban_week",
            "message": (
                "⚠️ You are cancelling less than 2 hours before your appointment. "
                "You have repeatedly cancelled appointments late this month. "
                "A 1-week booking restriction will be applied."
            ),
            "hours":   168
        }


def apply_cancellation_ban(db, driver_license: str, hours: int):
    if hours <= 0:
        return

    reason_map = {
        24:  "You cancelled an appointment less than 2 hours before your scheduled slot.",
        72:  "This is your second late cancellation this month.",
        168: "You have repeatedly cancelled appointments late this month.",
    }
    reason = reason_map.get(
        hours,
        "You cancelled an appointment less than 2 hours before your scheduled slot."
    )
    db.apply_suspension(driver_license, "late_cancellation", reason, hours)
