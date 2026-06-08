import re
import string
import random
from datetime import datetime, timedelta, date

VEHICLE_TYPES = [
    "Motorcycle (Personal)",
    "Motorcycle (Ride Share)",
    "CNG Auto",
    "Sedan",
    "SUV",
    "Microbus",
    "Truck",
    "Bus",
]

FUEL_TYPES = [
    "Octane",
    "Diesel",
    "Petrol",
    "Kerosene",
]


SLOT_DURATIONS = {
    "Motorcycle (Personal)":   4,
    "Motorcycle (Ride Share)": 4,
    "CNG Auto":                5,
    "Sedan":                   6,
    "SUV":                     7,
    "Microbus":                8,
    "Truck":                   12,
    "Bus":                     15,
}


EMERGENCY_CATEGORIES = [
    "ambulance",
    "fire",
    "police",
    "government",
    "military",
]

EMERGENCY_CATEGORY_LABELS = {
    "ambulance":  "🚑 Ambulance",
    "fire":       "🚒 Fire Service",
    "police":     "👮 Police Vehicle",
    "government": "🏛️ Government Vehicle",
    "military":   "⚔️ Military Vehicle",
}


BOOKING_PURPOSES = [
    "Daily commute",
    "Long distance travel",
    "Commercial vehicle",
    "Emergency",
]


FUEL_COLOURS = {
    "Octane":   "#1E90FF",
    "Diesel":   "#FFB300",
    "Petrol":   "#00C853",
    "Kerosene": "#FF6B35",
}


HEALTH_COLOURS = {
    "good":      "#00C853",
    "attention": "#FFB300",
    "action":    "#FF3D00",
    "unknown":   "#B0BEC5",
}

HEALTH_LABELS = {
    "good":      "🟢 Good",
    "attention": "🟡 Attention Needed",
    "action":    "🔴 Action Required",
    "unknown":   "⚪ Insufficient Data",
}


STATUS_LABELS = {
    "scheduled":        "📅 Scheduled",
    "serviced":         "✅ Serviced",
    "cancelled":        "❌ Cancelled",
    "no_show":          "⚠️ Missed",
    "pending_approval": "⏳ Pending Approval",
    "approved":         "✅ Approved",
    "denied":           "❌ Denied",
    "expired":          "⏰ Expired",
}

STATUS_COLOURS = {
    "scheduled":        "#1E90FF",
    "serviced":         "#00C853",
    "cancelled":        "#B0BEC5",
    "no_show":          "#FF3D00",
    "pending_approval": "#FFB300",
    "approved":         "#00C853",
    "denied":           "#FF3D00",
    "expired":          "#FF6B35",
}


WALKIN_DENIAL_REASONS = [
    "Station too busy",
    "Vehicle type not currently serviced",
    "Station closing soon",
    "Insufficient capacity today",
]


FUEL_SUPPLIERS = [
    "Bangladesh Petroleum Corp (BPC)",
    "Padma Oil Company",
    "Meghna Petroleum",
    "Jamuna Oil Company",
    "Other",
]


ETA_OPTIONS = [5, 10, 15, 20, 30, 45, 60, 90, 120]


CITIES_AREAS = {
    "Dhaka": [
        "Gulshan", "Banani", "Dhanmondi",
        "Mirpur", "Uttara", "Badda", "Mohammadpur"
    ],
    "Chattogram": [
        "Nasirabad", "Chandgaon", "Agrabad",
        "GEC", "Halishahar", "Khulshi"
    ],
}

ADJACENCY = {
    "Gulshan":     ["Banani", "Badda"],
    "Banani":      ["Gulshan", "Mohammadpur"],
    "Dhanmondi":   ["Mohammadpur", "Mirpur"],
    "Mirpur":      ["Dhanmondi", "Uttara"],
    "Uttara":      ["Mirpur"],
    "Badda":       ["Gulshan"],
    "Mohammadpur": ["Dhanmondi", "Banani"],
    "Nasirabad":   ["Chandgaon", "GEC"],
    "Chandgaon":   ["Nasirabad", "Halishahar"],
    "Agrabad":     ["GEC", "Halishahar"],
    "GEC":         ["Nasirabad", "Agrabad", "Khulshi"],
    "Halishahar":  ["Chandgaon", "Agrabad"],
    "Khulshi":     ["GEC"],
}

_DL_RE = re.compile(
    r"^DL-(DHK|CTG|SYL|RJH|KHL|BAR|RNG|MYM|GOV|PDB|STN)-\d{4}-\d{4}$"
)


_PLATE_STANDARD_RE = re.compile(
    r"^(DHAKA|CTG|SYLHET|RAJSHAHI|KHULNA|BARISAL|RANGPUR|MYMENSINGH)"
    r"-(METRO|CITY|DISTRICT)-[A-Z]{2}-\d{2}-\d{4}$"
)


_PLATE_RS_RE = re.compile(
    r"^RS-(DHAKA|CTG|SYLHET|RAJSHAHI|KHULNA|BARISAL|RANGPUR|MYMENSINGH)"
    r"-[A-Z]{2}-\d{2}-\d{4}$"
)


_EMERGENCY_REG_RE = re.compile(
    r"^(FIRE|AMB|POL|GOVT|MIL)-(DHK|CTG|SYL|RJH|KHL|BAR|BD)-\d{3}$"
)


_EMAIL_RE = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def validate_driver_license(dl: str) -> tuple:

    if not dl or not dl.strip():
        return False, "Driver's license cannot be empty."
    cleaned = dl.strip().upper()
    if _DL_RE.match(cleaned):
        return True, cleaned
    return False, (
        "Driver's license format is invalid. "
        "Expected format: DL-DHK-2341-2021 "
        "(City codes: DHK, CTG, SYL, RJH, KHL, BAR, RNG, MYM)"
    )


def validate_license_plate(plate: str, vehicle_type: str = None) -> tuple:

    if not plate or not plate.strip():
        return False, "License plate cannot be empty."

    cleaned = plate.strip().upper()

    is_standard = bool(_PLATE_STANDARD_RE.match(cleaned))
    is_rs       = bool(_PLATE_RS_RE.match(cleaned))

    if not is_standard and not is_rs:
        return False, (
            "License plate format is invalid. "
            "Standard format: DHAKA-METRO-GA-11-2233 "
            "Ride Share format: RS-DHAKA-KA-12-3344"
        )

   
    if vehicle_type:
        if vehicle_type == "Motorcycle (Ride Share)" and not is_rs:
            return False, (
                "Ride Share motorcycles must use the commercial "
                "registration format starting with RS-. "
                "Example: RS-DHAKA-KA-05-1122"
            )
        if vehicle_type == "Motorcycle (Personal)" and is_rs:
            return False, (
                "This plate appears to be a ride share registration. "
                "Please select 'Motorcycle (Ride Share)' as your vehicle type."
            )

    return True, cleaned


def validate_emergency_registration(reg: str) -> tuple:

    if not reg or not reg.strip():
        return False, "Vehicle registration cannot be empty."
    cleaned = reg.strip().upper()
    if _EMERGENCY_REG_RE.match(cleaned):
        return True, cleaned
    return False, (
        "Invalid emergency vehicle registration format. "
        "Expected: AMB-DHK-001 or FIRE-CTG-042"
    )


def validate_email(email: str) -> tuple:

    if not email or not email.strip():
        return False, "Email address cannot be empty."
    cleaned = email.strip().lower()
    if _EMAIL_RE.match(cleaned):
        return True, cleaned
    return False, "Please enter a valid email address."


def validate_fuel_amount(amount, daily_limit: float,
                         available: float) -> tuple:

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return False, "Please enter a valid fuel amount."

    if amount <= 0:
        return False, "Fuel amount must be greater than zero."

    if amount != int(amount):
        return False, "Fuel amount must be a whole number (no decimals)."

    amount = int(amount)

    if amount > daily_limit:
        return False, (
            f"Requested amount exceeds your daily limit of {int(daily_limit)}L "
            f"for this vehicle and fuel type."
        )

    if amount > available:
        return False, (
            f"Requested amount exceeds available stock at this station. "
            f"Please request {int(available)}L or less."
        )

    return True, ""


def validate_dispensed_amount(actual, requested: float) -> tuple:

    try:
        actual = round(float(actual), 1)
    except (TypeError, ValueError):
        return False, "Please enter a valid dispensed amount."

    if actual <= 0:
        return False, "Dispensed amount must be greater than zero."

    if actual > requested:
        return False, (
            f"Dispensed amount cannot exceed the requested amount of {requested}L."
        )

    return True, actual


def validate_resupply_amount(quantity, remaining_capacity: float) -> tuple:

    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        return False, "Please enter a valid quantity."

    if quantity <= 0:
        return False, "Resupply quantity must be greater than zero."

    if quantity != int(quantity):
        return False, "Resupply quantity must be a whole number."

    quantity = int(quantity)

    if quantity > remaining_capacity:
        return False, (
            f"Resupply amount exceeds remaining tank capacity. "
            f"Maximum you can add: {int(remaining_capacity)}L"
        )

    return True, quantity


def validate_fuel_price(price) -> tuple:

    try:
        price = round(float(price), 2)
    except (TypeError, ValueError):
        return False, "Please enter a valid price."

    if price <= 0:
        return False, "Fuel price must be greater than zero."

    if price < 50:
        return False, "Fuel price seems too low. Minimum is ৳50/L."

    if price > 500:
        return False, "Fuel price seems too high. Maximum is ৳500/L."

    return True, price


def validate_eta_minutes(eta) -> tuple:

    try:
        eta = int(eta)
    except (TypeError, ValueError):
        return False, "Please select a valid ETA."

    if eta < 5:
        return False, "ETA must be at least 5 minutes."

    if eta > 120:
        return False, (
            "For arrivals more than 2 hours away, "
            "please use the standard advance booking system instead."
        )

    return True, eta


def validate_announcement(title: str, message: str,
                           expires_at) -> tuple:

    if not title or not title.strip():
        return False, "Please enter an announcement title."
    if len(title.strip()) < 5:
        return False, "Title must be at least 5 characters."
    if len(title.strip()) > 100:
        return False, "Title cannot exceed 100 characters."

    if not message or not message.strip():
        return False, "Please enter an announcement message."
    if len(message.strip()) < 10:
        return False, "Message must be at least 10 characters."
    if len(message.strip()) > 500:
        return False, "Message cannot exceed 500 characters."

    if expires_at is None:
        return False, "Please set an expiry date."

    now = datetime.now()
    try:
        if isinstance(expires_at, date) and not isinstance(expires_at, datetime):
            expires_dt = datetime.combine(expires_at, datetime.max.time())
        else:
            expires_dt = expires_at
        if expires_dt <= now + timedelta(hours=1):
            return False, "Expiry must be at least 1 hour in the future."
        if expires_dt > now + timedelta(days=30):
            return False, "Announcements cannot be scheduled more than 30 days ahead."
    except Exception:
        return False, "Invalid expiry date."

    return True, ""


def validate_schedule(start_dt, end_dt) -> tuple:

    now = datetime.now()

    if start_dt is None or end_dt is None:
        return False, "Please set both start and end times."

    try:
        if isinstance(start_dt, date) and not isinstance(start_dt, datetime):
            start_dt = datetime.combine(start_dt, datetime.min.time())
        if isinstance(end_dt, date) and not isinstance(end_dt, datetime):
            end_dt = datetime.combine(end_dt, datetime.min.time())
    except Exception:
        return False, "Invalid date format."

    if start_dt < now + timedelta(minutes=15):
        return False, "Start time must be at least 15 minutes in the future."

    if end_dt <= start_dt:
        return False, "End time must be after start time."

    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    if duration_hours < 0.5:
        return False, "Schedule duration must be at least 30 minutes."

    if duration_hours > 12:
        return False, (
            "A single schedule cannot exceed 12 hours. "
            "Please create multiple entries for longer outages."
        )

    return True, ""



def generate_token(db=None) -> str:

    chars = string.ascii_uppercase + string.digits
    for _ in range(100):  # max attempts
        token = "".join(random.choices(chars, k=8))
        if token.startswith("EX"):
            continue
        if db is None:
            return token
        if not db.token_exists(token):
            return token

    raise RuntimeError("Could not generate unique token after 100 attempts.")


def generate_emergency_token(db=None) -> str:

    chars = string.ascii_uppercase + string.digits
    for _ in range(100):
        suffix = "".join(random.choices(chars, k=8))
        token  = f"EX-{suffix}"
        if db is None:
            return token
        if not db.token_exists(token):
            return token
    raise RuntimeError("Could not generate unique emergency token.")


def generate_temp_password() -> str:

    digits = "".join(random.choices(string.digits, k=6))
    return f"TEMP-{digits}"



def format_datetime(dt_str: str, include_time: bool = True) -> str:

    if not dt_str:
        return "—"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        if include_time:
            return dt.strftime("%A, %B %d, %Y at %I:%M %p")
        return dt.strftime("%A, %B %d, %Y")
    except Exception:
        return dt_str


def format_time_only(dt_str: str) -> str:

    if not dt_str:
        return "—"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%I:%M %p")
    except Exception:
        return dt_str


def format_date_only(dt_str: str) -> str:

    if not dt_str:
        return "—"
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %d, %Y")
    except Exception:
        return dt_str


def get_schedule_status(start_str: str, end_str: str) -> str:

    if not start_str or not end_str:
        return "unknown"
    try:
        now   = datetime.now()
        start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end   = datetime.strptime(end_str,   "%Y-%m-%d %H:%M:%S")
        if start <= now <= end:
            return "active"
        elif now < start:
            return "upcoming"
        else:
            return "expired"
    except Exception:
        return "unknown"


def get_schedule_status_label(status: str) -> str:
    labels = {
        "active":   "⚡ Active Now",
        "upcoming": "🕐 Upcoming",
        "expired":  "✅ Expired",
        "unknown":  "❓ Unknown",
    }
    return labels.get(status, status)


def format_duration(start_str: str, end_str: str) -> str:

    if not start_str or not end_str:
        return "—"
    try:
        start    = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
        end      = datetime.strptime(end_str,   "%Y-%m-%d %H:%M:%S")
        total_m  = int((end - start).total_seconds() / 60)
        hours    = total_m // 60
        minutes  = total_m % 60
        if hours > 0 and minutes > 0:
            return f"{hours} hr {minutes} min"
        elif hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"{minutes} minutes"
    except Exception:
        return "—"


def is_slot_late(slot_datetime_str: str) -> bool:

    if not slot_datetime_str:
        return False
    try:
        slot = datetime.strptime(slot_datetime_str, "%Y-%m-%d %H:%M:%S")
        now  = datetime.now()
        return (
            slot.date() == now.date()  # same day
            and slot < now             # slot time has passed
        )
    except Exception:
        return False


def is_slot_expired(slot_datetime_str: str) -> bool:

    if not slot_datetime_str:
        return False
    try:
        slot = datetime.strptime(slot_datetime_str, "%Y-%m-%d %H:%M:%S")
        return slot.date() < date.today()
    except Exception:
        return False


def get_slot_hold_deadline(minutes: int = 10) -> str:

    deadline = datetime.now() + timedelta(minutes=minutes)
    return deadline.strftime("%I:%M %p")


def is_slot_hold_valid(hold_until_str: str) -> bool:

    if not hold_until_str:
        return False
    try:
        now      = datetime.now()
        hold_dt  = datetime.strptime(
            f"{now.strftime('%Y-%m-%d')} {hold_until_str}",
            "%Y-%m-%d %I:%M %p"
        )
        return now <= hold_dt
    except Exception:
        return False


def get_eta_datetime(eta_minutes: int) -> str:

    eta_dt = datetime.now() + timedelta(minutes=eta_minutes)
    return eta_dt.strftime("%Y-%m-%d %H:%M:%S")


def get_waitlist_offer_window(station_closing_time: str) -> int:

    if not station_closing_time:
        return 30

    try:
        now         = datetime.now()
        close_h, close_m = map(int, station_closing_time.split(":"))
        closing     = datetime.combine(
            date.today(),
            datetime.min.time().replace(hour=close_h, minute=close_m)
        )
        mins_until_closing = int((closing - now).total_seconds() / 60)

        if mins_until_closing < 5:
            return 0  # Hold until tomorrow
        return min(30, mins_until_closing)
    except Exception:
        return 30

def calculate_cost(amount: float, price_per_litre: float) -> float:

    return round(amount * price_per_litre, 2)


def format_currency(amount: float) -> str:

    return f"৳{amount:,.2f}"


def format_currency_int(amount: float) -> str:

    return f"৳{int(amount):,}"



def generate_receipt_text(booking: dict, station_name: str,
                           actual_amount: float,
                           serviced_at: str) -> str:

    price      = booking.get("price_per_litre", 0)
    actual_cost = calculate_cost(actual_amount, price)

    lines = [
        "═══════════════════════════════════════",
        "    CHOLAR SHONGI — SERVICE RECEIPT    ",
        "═══════════════════════════════════════",
        f"Token:        {booking.get('token', '—')}",
        f"Date:         {format_date_only(serviced_at)}",
        f"Serviced At:  {format_time_only(serviced_at)}",
        f"Station:      {station_name}",
        "───────────────────────────────────────",
        f"Vehicle:      {booking.get('vehicle_type', '—')}",
        f"Plate:        {booking.get('license_plate', '—')}",
        f"Fuel:         {booking.get('fuel_type', '—')}",
        f"Dispensed:    {actual_amount}L",
        f"Price:        {format_currency(price)}/L",
        f"Total:        {format_currency(actual_cost)}",
        "───────────────────────────────────────",
        "Status:       ✅ SERVICED",
        "═══════════════════════════════════════",
    ]
    return "\n".join(lines)


def generate_emergency_receipt_text(booking: dict, station_name: str,
                                     actual_amount: float,
                                     serviced_at: str) -> str:

    price       = booking.get("price_per_litre", 0)
    actual_cost = calculate_cost(actual_amount, price)

    lines = [
        "═══════════════════════════════════════",
        "  CHOLAR SHONGI — EMERGENCY RECEIPT   ",
        "═══════════════════════════════════════",
        f"Token:        {booking.get('token', '—')}",
        f"Date:         {format_date_only(serviced_at)}",
        f"Serviced At:  {format_time_only(serviced_at)}",
        f"Station:      {station_name}",
        "───────────────────────────────────────",
        f"Registration: {booking.get('registration_number', '—')}",
        f"Category:     {booking.get('vehicle_category', '—').title()}",
        f"Organisation: {booking.get('organisation', '—')}",
        f"Fuel:         {booking.get('fuel_type', '—')}",
        f"Dispensed:    {actual_amount}L",
        f"Price:        {format_currency(price)}/L",
        f"Total:        {format_currency(actual_cost)}",
        "───────────────────────────────────────",
        "Status:       ✅ SERVICED (EMERGENCY)",
        "═══════════════════════════════════════",
    ]
    return "\n".join(lines)

def get_fuel_gauge_colour(stock: float, capacity: float) -> str:

    if capacity <= 0:
        return "#B0BEC5"
    pct = (stock / capacity) * 100
    if pct > 50:
        return "#00C853"
    elif pct > 15:
        return "#FFB300"
    else:
        return "#FF3D00"


def get_fuel_pct(stock: float, capacity: float) -> float:

    if capacity <= 0:
        return 0.0
    return round((stock / capacity) * 100, 1)


def get_adjacent_areas(area: str) -> list:

    return ADJACENCY.get(area, [])



def get_default_expiry_date():
    """Default announcement expiry: 7 days from now."""
    return (datetime.now() + timedelta(days=7)).date()


def format_suspension_message(suspension: dict) -> str:

    if not suspension:
        return ""
    try:
        until_dt  = datetime.strptime(
            suspension["suspended_until"], "%Y-%m-%d %H:%M:%S"
        )
        until_str = until_dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        until_str = suspension.get("suspended_until", "—")

    reason = suspension.get("reason", "Booking restriction applied.")
    return (
        f"Your booking access is restricted until {until_str}. "
        f"Reason: {reason}"
    )


def get_booking_type_label(booking_type: str) -> str:
    labels = {
        "advance":   "📅 Advance",
        "walkin":    "🚶 Walk-In",
        "emergency": "🚨 Emergency",
    }
    return labels.get(booking_type, booking_type.title())


def get_cities() -> list:
    return sorted(CITIES_AREAS.keys())


def get_areas(city: str) -> list:
    return sorted(CITIES_AREAS.get(city, []))


def get_slot_duration(vehicle_type: str) -> int:

    return SLOT_DURATIONS.get(vehicle_type, 6)


def mask_token(token: str) -> str:

    if not token:
        return "—"
    if token.startswith("EX-"):
        suffix = token[3:]
        return f"EX-XXXX-{suffix[-4:]}"
    return f"XXXX-{token[-4:]}"


def format_walkin_denial_reason(reason: str) -> str:

    if reason in WALKIN_DENIAL_REASONS:
        return reason
    return "Station unable to accommodate request."
