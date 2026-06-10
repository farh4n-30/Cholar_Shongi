import os
os.environ["TZ"] = "Asia/Dhaka"
try:
    import time
    time.tzset()
except AttributeError:
    pass

import streamlit as st
import sys


st.set_page_config(
    page_title="চলার সঙ্গী | Cholar Shongi",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from auth import (
    login_user, logout_user, register_user,
    get_active_suspension_message, require_role
)
from views import (

    show_electricity_public,
    show_pdb_dashboard,
    show_advance_booking,
    show_walkin_booking,
    show_emergency_services,
    show_find_my_booking,
    show_station_dashboard,
    show_verify_token,
    show_station_analytics,
    show_pump_management,
    show_inventory_management,
    show_govt_control_panel,
)
from email_service import send_email
import utils

def init_session_state():
    defaults = {
        "logged_in":        False,
        "role":             None,
        "user_id":          None,
        "user_name":        None,
        "driver_license":   None,
        "email":            None,
        "station_id":       None,
        "assigned_city":    None,
        "current_segment":  "landing",
        "govt_view":        None,
        "slot_hold":        None,
        "slot_hold_until":  None,
        "booking_step":     1,
        "selected_city":    None,
        "selected_area":    None,
        "selected_station": None,
        "selected_vehicle": None,
        "selected_fuel":    None,
        "requested_amount": None,
        "selected_slot":    None,
        "force_pw_change":  False,
        "fuel_view": None,
        "show_postpone": False,
        "show_cancel_confirm": False,
        "show_full_grid": False,
        "confirm_station_close": False,
        "show_lift": None,
        "emr_verified": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

@st.cache_resource
def get_db():
    return DatabaseManager()

db = get_db()
db.cleanup_expired()

CHOLAR_SHONGI_MANUAL = """
CHOLAR SHONGI — OFFICIAL USER MANUAL
Version 1.0 | Bangladesh Fuel & Power Management

SECTION 1: GETTING STARTED
Cholar Shongi (চলার সঙ্গী) is Bangladesh's smart guide to fuel booking
and electricity schedule management. The app has two main segments:
  Electricity: Check power cut schedules for your area.
  Fuel: Book fuel appointments at stations.
No login is needed to check electricity schedules.
Fuel booking requires registration.

SECTION 2: REGISTERING AS A USER
1. Click Fuel from the home page.
2. In the sidebar click Register.
3. Enter your full name.
4. Enter your email address.
5. Enter your Driver's License number.
   Format: DL-DHK-2341-2021
   City codes: DHK, CTG, SYL, RJH, KHL, BAR, RNG, MYM
6. Create a password (min 8 characters, uppercase, lowercase, number).
7. Click Register. You are now logged in.
Note: One account per driver's license.

SECTION 3: CHECKING ELECTRICITY SCHEDULES
1. Click Electricity from the home page.
2. Select your City then Area.
3. See Active Now, Upcoming and Expired schedules.
4. If schedules were updated in the last 48 hours a notice appears.
5. Schedules shown up to 7 days ahead only.

SECTION 4: BOOKING A FUEL APPOINTMENT
1. Login from the Fuel segment sidebar.
2. Click Advance Booking.
3. Select City, Area and Station.
4. Select Vehicle Type and Fuel Type.
   Your daily limit and current price are shown.
5. Enter how many litres you need (cannot exceed daily limit).
6. The system suggests the best available slot.
   Browse all slots for next 3 days if preferred.
   If no slots available, you may join the waitlist.
7. Click your preferred time slot.
   A deadline is shown — complete booking before this time.
8. Enter your License Plate number.
   Standard: DHAKA-METRO-GA-11-2233
   Ride Share Motorcycle: RS-DHAKA-KA-05-1122
9. Optionally select a booking purpose.
10. Review booking summary. Click Confirm Booking.
11. Save your 8-character token. Show it to the station operator.

Important rules:
Each vehicle may only be booked once per calendar day.
You must arrive on the same calendar day as your appointment.
Online booking closes 1 hour before station closing time.

SECTION 5: ON-DEMAND (WALK-IN) BOOKING
Walk-in booking is for:
1. Passing a station and wanting to refuel immediately.
2. A station has free capacity after a missed appointment.
Only available at stations where walk-ins are enabled.
1. Click Walk-In Booking and login.
2. Select station, vehicle, fuel type and amount.
3. Submit your request.
4. Wait for admin to approve. Click Check Approval Status.
5. If approved: token is generated immediately.
6. If denied: reason shown. No penalty applies.
Walk-in bookings cannot be postponed after approval.

SECTION 6: EMERGENCY SERVICES
For registered emergency vehicles only.
1. Click Emergency Services. No login required.
2. Enter vehicle registration number. Example: AMB-DHK-001
3. If verified and category is enabled, proceed.
4. Enter driver's license, select fuel type, city and area.
5. Stations shown with actual fuel stock levels.
6. Select station, enter fuel amount and ETA in minutes.
7. Emergency token begins with EX-. Show it to the operator.
Emergency bookings are independent from personal bookings.
Personal suspensions do not affect emergency service access.

SECTION 7: FIND MY BOOKING
Without login: Enter Driver's License.
  See station, time, status and masked token.
With login: See full token and manage your booking.

SECTION 8A: JOINING THE WAITLIST
When no slots are available, Join Waitlist appears instead.
1. Click Join Waitlist.
2. When a slot opens during operating hours you are notified.
3. Accept within the offer window to confirm booking.
4. If you decline or do not respond, slot goes to next person.
Rules:
  One waitlist entry per vehicle per day.
  You can book at a different station while waitlisted.
  If you do, your waitlist entry is automatically removed.
  Leave the waitlist anytime from Find My Booking.
  No penalty for leaving or for expired entries.

SECTION 8: POSTPONING AN APPOINTMENT
Available for advance bookings only.
1. Go to Find My Booking (logged in).
2. Click Postpone Appointment (at least 1 hour before slot).
3. Select new slot up to 3 days forward at same station.
4. Token remains unchanged.
If no slots available:
  Added to postponement waitlist.
  Original booking stays active.
  If slot opens within 3 days, offered to you first.
  If accepted: counts as 1 postponement.
  If no slot in 3 days: cancelled with no penalty.
Limits: Maximum 3 successful postponements per month.
No penalty ever applies for postponing.

SECTION 9: CANCELLING AN APPOINTMENT
1. Go to Find My Booking (logged in).
2. Click Cancel and confirm.
Cancel 2+ hours before: No consequence.
Cancel less than 2 hours before:
  1st time this month: 24 hour restriction.
  2nd time this month: 72 hour restriction.
  3rd time this month: 1 week restriction.

SECTION 10: CONDUCT POLICY
Missed appointments:
  1st: Warning only.
  2nd within 6 months: 1 week restriction.
  3rd lifetime: 2 week restriction.
  4th lifetime: 1 month restriction.
  5th lifetime: Account flagged for review.
Late arrivals (same day): Token still valid, no penalty.
All restrictions state exact reason and lift time.

SECTION 11: FOR STATION ADMINS
Login from Fuel segment sidebar under Station Admin Login.
Dashboard: Appointments tab and Requests tab (walk-in approvals).
Verify Token: type token, enter actual litres, mark as serviced.
Analytics: performance charts with week/month/year filter.
Pump Management: plan maintenance or emergency close.
Inventory: fuel levels, enable walk-ins, log resupply.

SECTION 12: FOR PDB ADMINS
Login from Electricity segment sidebar.
Publish: select feeder, set start and end time, add note.
  Min 30 minutes. Max 12 hours. No overlap on same feeder.
  Start must be at least 15 minutes in the future.
Manage: edit or delete existing schedules.
History: view all schedules with filters.
Schedules beyond 7 days are hidden from public automatically.

SECTION 13: FOR GOVERNMENT OFFICIALS
Login from the main landing page sidebar.
Select Fuel Management or Electricity Management.
Fuel: analytics, stock trajectory, station comparison,
  daily limits, prices, special vehicles, announcements,
  password reset, search, audit log.
Electricity: outage analytics, PDB audit log.

SECTION 14: TROUBLESHOOTING
Appointments currently closed: Try another station or fuel type.
Access restricted: Message shows exact reason and lift time.
Token not valid for this station: Token belongs to another station.
Walk-in not accepted: Station has walk-ins disabled.
Slot hold expired: Select a new slot.
Vehicle not in emergency registry: Contact district authority.
"""

def inject_css():
    st.markdown("""
    <style>
    /* Card styling */
    .segment-card {
        background: #132039;
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        border: 1px solid #1E90FF22;
        transition: border-color 0.3s;
        cursor: pointer;
    }
    .segment-card:hover {
        border-color: #1E90FF;
    }
    /* Hero section */
    .hero-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1E90FF, #00C853);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.2rem;
        color: #B0BEC5;
        text-align: center;
        margin-bottom: 1rem;
    }
    /* Status badges */
    .badge-active {
        background: #FF3D0022;
        color: #FF3D00;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid #FF3D00;
    }
    .badge-upcoming {
        background: #FFB30022;
        color: #FFB300;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid #FFB300;
    }
    .badge-expired {
        background: #00C85322;
        color: #00C853;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        border: 1px solid #00C853;
    }
    /* Token display */
    .token-box {
        background: #132039;
        border: 2px solid #1E90FF;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin: 16px 0;
    }
    .token-text {
        font-size: 2.5rem;
        font-weight: 900;
        color: #1E90FF;
        letter-spacing: 6px;
        font-family: monospace;
    }
    /* Alert boxes */
    .alert-critical {
        background: #FF3D0015;
        border-left: 4px solid #FF3D00;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .alert-warning {
        background: #FFB30015;
        border-left: 4px solid #FFB300;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
    .alert-info {
        background: #1E90FF15;
        border-left: 4px solid #1E90FF;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
    }
    /* Fuel gauge bars */
    .fuel-gauge-bg {
        background: #0A1628;
        border-radius: 8px;
        height: 12px;
        width: 100%;
        overflow: hidden;
    }
    /* Receipt */
    .receipt-box {
        background: #132039;
        border: 1px solid #1E90FF44;
        border-radius: 12px;
        padding: 24px;
        font-family: monospace;
        max-width: 400px;
        margin: 0 auto;
    }
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

inject_css()

def load_lottie(url):
    try:
        import requests
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def show_lottie(url, height=200, fallback="⚡"):
    try:
        from streamlit_lottie import st_lottie
        data = load_lottie(url)
        if data:
            st_lottie(data, height=height, key=url)
            return
    except Exception:
        pass
    st.markdown(
        f"<div style='text-align:center;font-size:80px;padding:20px'>{fallback}</div>",
        unsafe_allow_html=True
    )

def show_landing_sidebar():
    with st.sidebar:
        st.markdown("### চলার সঙ্গী")
        st.markdown("---")
        st.download_button(
            label="📥 Download User Manual",
            data=CHOLAR_SHONGI_MANUAL.encode("utf-8"),
            file_name="Cholar_Shongi_User_Manual.txt",
            mime="text/plain; charset=utf-8",
            use_container_width=True
        )

        st.markdown("---")
        st.markdown("### 🏛️ Government Official")
        if not st.session_state.logged_in:
            with st.form("govt_login_form"):
                govt_email = st.text_input("Email", key="govt_email_input")
                govt_pass  = st.text_input("Password", type="password",
                                           key="govt_pass_input")
                submitted  = st.form_submit_button("Login",
                                                   use_container_width=True)
                if submitted:
                    result = login_user(db, govt_email, govt_pass)
                    if result["success"]:
                        if result["role"] == "government_official":
                            for k, v in result.items():
                                if k != "success":
                                    st.session_state[k] = v
                            st.session_state.logged_in = True
                            st.session_state.current_segment = "govt"
                            st.rerun()
                        else:
                            st.error("This login is for Government Officials only.")
                    else:
                        st.error(result["message"])
        else:
            if st.session_state.role == "government_official":
                st.success(f"Welcome, {st.session_state.user_name}")
                if st.button("Logout", use_container_width=True):
                    logout_user()
                    st.rerun()

def show_electricity_sidebar():
    with st.sidebar:
        st.markdown("### ⚡ Electricity")
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.current_segment = "landing"
            st.rerun()
        st.markdown("---")

        if not st.session_state.logged_in:
            st.markdown("**⚡ PDB Admin Login**")
            with st.form("pdb_login_form"):
                pdb_email = st.text_input("Email", key="pdb_email_input")
                pdb_pass  = st.text_input("Password", type="password",
                                          key="pdb_pass_input")
                submitted = st.form_submit_button("Login",
                                                  use_container_width=True)
                if submitted:
                    result = login_user(db, pdb_email, pdb_pass)
                    if result["success"]:
                        if result["role"] == "pdb_admin":
                            for k, v in result.items():
                                if k != "success":
                                    st.session_state[k] = v
                            st.session_state.logged_in = True
                            st.rerun()
                        else:
                            st.error("This login is for PDB Admins only.")
                    else:
                        st.error(result["message"])
        else:
            if st.session_state.role == "pdb_admin":
                st.success(f"Welcome,\n{st.session_state.user_name}")
                st.caption(f"City: {st.session_state.assigned_city}")
                if st.button("Logout", use_container_width=True):
                    logout_user()
                    st.rerun()

def show_fuel_sidebar():
    with st.sidebar:
        st.markdown("### ⛽ Fuel Services")
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.current_segment = "landing"
            st.rerun()
        st.markdown("---")

        if st.session_state.logged_in:
            role = st.session_state.role
            if role == "user":
                st.success(f"👤 {st.session_state.user_name}")
                if st.button("Logout", use_container_width=True):
                    logout_user()
                    st.rerun()
            elif role == "station_admin":
                st.success(f"🏪 {st.session_state.user_name}")
                if st.button("Logout", use_container_width=True):
                    logout_user()
                    st.rerun()
        else:
            with st.expander("👤 User Login / Register", expanded=True):
                tab_login, tab_reg = st.tabs(["Login", "Register"])

                with tab_login:
                    with st.form("user_login_form"):
                        identifier = st.text_input(
                            "Email or Driver's License",
                            key="user_login_identifier"
                        )
                        password = st.text_input(
                            "Password", type="password",
                            key="user_login_password"
                        )
                        submitted = st.form_submit_button(
                            "Login", use_container_width=True
                        )
                        if submitted:
                            result = login_user(db, identifier, password)
                            if result["success"]:
                                if result["role"] in ("user",):
                                    for k, v in result.items():
                                        if k != "success":
                                            st.session_state[k] = v
                                    st.session_state.logged_in = True
                                    st.rerun()
                                else:
                                    st.error("Please use the correct login section.")
                            else:
                                st.error(result["message"])

                with tab_reg:
                    with st.form("register_form"):
                        reg_name = st.text_input("Full Name", key="reg_name")
                        reg_email = st.text_input("Email", key="reg_email")
                        reg_dl = st.text_input(
                            "Driver's License",
                            placeholder="DL-DHK-2341-2021",
                            key="reg_dl"
                        )
                        reg_pass = st.text_input(
                            "Password", type="password", key="reg_pass"
                        )
                        reg_pass2 = st.text_input(
                            "Confirm Password", type="password",
                            key="reg_pass2"
                        )
                        reg_submitted = st.form_submit_button(
                            "Register", use_container_width=True
                        )
                        if reg_submitted:
                            result = register_user(
                                db, reg_name, reg_email,
                                reg_dl, reg_pass, reg_pass2
                            )
                            if result["success"]:
                                for k, v in result.items():
                                    if k != "success":
                                        st.session_state[k] = v
                                st.session_state.logged_in = True
                                st.success("Registration successful!")
                                st.rerun()
                            else:
                                st.error(result["message"])

            with st.expander("🏪 Station Admin Login"):
                with st.form("station_login_form"):
                    stn_email = st.text_input("Email", key="stn_email")
                    stn_pass  = st.text_input("Password", type="password",
                                              key="stn_pass")
                    submitted = st.form_submit_button(
                        "Login", use_container_width=True
                    )
                    if submitted:
                        result = login_user(db, stn_email, stn_pass)
                        if result["success"]:
                            if result["role"] == "station_admin":
                                for k, v in result.items():
                                    if k != "success":
                                        st.session_state[k] = v
                                st.session_state.logged_in = True
                                st.rerun()
                            else:
                                st.error("This login is for Station Admins only.")
                        else:
                            st.error(result["message"])

def show_landing_page():
    show_landing_sidebar()
    st.markdown(
        '<div class="hero-title">চলার সঙ্গী</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div class="hero-subtitle">Cholar Shongi — Your smart guide to energy and fuel in Bangladesh</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="text-align:center;padding-left:20px;font-style:italic;color:#00C853;">'
        'Seamless fuel. Scheduled power. Zero hassle.</p>',
        unsafe_allow_html=True
    )

    show_lottie(
        "https://assets4.lottiefiles.com/packages/lf20_touohxv0.json",
        height=180,
        fallback="🏙️"
    )

    st.markdown("---")
    announcements = db.get_active_announcements()
    if announcements:
        for ann in announcements:
            st.markdown(
                f'<div class="alert-info">📢 <strong>{ann["title"]}</strong>: {ann["message"]}</div>',
                unsafe_allow_html=True
            )
        st.markdown("")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:60px">⚡</div>
            <h2 style="color:#1E90FF;margin:8px 0">Electricity</h2>
            <p style="color:#B0BEC5">Check load shedding schedules for your area. No login required.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Explore Electricity →", key="btn_electricity",
                     use_container_width=True):
            st.session_state.current_segment = "electricity"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:60px">⛽</div>
            <h2 style="color:#00C853;margin:8px 0">Fuel</h2>
            <p style="color:#B0BEC5">Book fuel appointments at stations near you. Register to get started.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Explore Fuel →", key="btn_fuel",
                     use_container_width=True):
            st.session_state.current_segment = "fuel"
            st.rerun()

def show_electricity_segment():
    show_electricity_sidebar()

    role = st.session_state.role if st.session_state.logged_in else None

    if role == "pdb_admin":
        if st.session_state.get("force_pw_change"):
            show_force_password_change()
            return
        show_pdb_dashboard(db)
    else:
        show_electricity_public(db)

def show_fuel_segment():
    show_fuel_sidebar()

    role = st.session_state.role if st.session_state.logged_in else None

    if st.session_state.logged_in and st.session_state.get("force_pw_change"):
        show_force_password_change()
        return

    if role == "station_admin":
        show_station_admin_view()
    elif role == "user":
        show_user_fuel_view()
    else:
        show_public_fuel_view()


def show_public_fuel_view():
    """What the public sees in the fuel segment — no login."""
    st.markdown("## ⛽ Fuel Services")
    show_lottie(
        "https://assets4.lottiefiles.com/packages/lf20_CXxysR.json",
        height=150,
        fallback="⛽"
    )

    announcements = db.get_active_announcements()
    for ann in announcements:
        st.markdown(
            f'<div class="alert-info">📢 <strong>{ann["title"]}</strong>: {ann["message"]}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    col1, col2 = st.columns(2, gap="medium")
    col3, col4 = st.columns(2, gap="medium")

    with col1:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:40px">📅</div>
            <h3 style="color:#1E90FF">Advance Booking</h3>
            <p style="color:#B0BEC5;font-size:0.9rem">Book up to 3 days ahead. Requires login.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Advance Booking", key="pub_advance",
                     use_container_width=True):
            st.info("Please login to make an advance booking.")

    with col2:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:40px">🚶</div>
            <h3 style="color:#00C853">Walk-In Booking</h3>
            <p style="color:#B0BEC5;font-size:0.9rem">Already at a station? Request service now. Requires login.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Walk-In Booking", key="pub_walkin",
                     use_container_width=True):
            st.info("Please login to submit a walk-in request.")

    with col3:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:40px">🚨</div>
            <h3 style="color:#FF3D00">Emergency Services</h3>
            <p style="color:#B0BEC5;font-size:0.9rem">Registered emergency vehicles. No login required.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Emergency Services", key="pub_emergency",
                     use_container_width=True):
            st.session_state.fuel_view = "emergency"
            st.rerun()

    with col4:
        st.markdown("""
        <div class="segment-card">
            <div style="font-size:40px">🔍</div>
            <h3 style="color:#FFD700">Find My Booking</h3>
            <p style="color:#B0BEC5;font-size:0.9rem">Retrieve your token using your driver's license.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Find My Booking", key="pub_find",
                     use_container_width=True):
            st.session_state.fuel_view = "find"
            st.rerun()

    fuel_view = st.session_state.get("fuel_view")
    if fuel_view == "emergency":
        st.markdown("---")
        show_emergency_services(db)
    elif fuel_view == "find":
        st.markdown("---")
        show_find_my_booking(db, logged_in=False)


def show_user_fuel_view():
    suspension_msg = get_active_suspension_message(
        db, st.session_state.driver_license
    )

    st.markdown(f"## ⛽ Welcome, {st.session_state.user_name}")

    announcements = db.get_active_announcements()
    for ann in announcements:
        st.markdown(
            f'<div class="alert-info">📢 <strong>{ann["title"]}</strong>: {ann["message"]}</div>',
            unsafe_allow_html=True
        )

    if suspension_msg:
        st.markdown(
            f'<div class="alert-critical">🚫 {suspension_msg}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    tabs = st.tabs([
        "📅 Advance Booking",
        "🚶 Walk-In Booking",
        "🚨 Emergency Services",
        "🔍 Find My Booking"
    ])

    with tabs[0]:
        if suspension_msg:
            st.error(suspension_msg)
        else:
            show_advance_booking(db)

    with tabs[1]:
        if suspension_msg:
            st.error(suspension_msg)
        else:
            show_walkin_booking(db)

    with tabs[2]:
        show_emergency_services(db)

    with tabs[3]:
        show_find_my_booking(db, logged_in=True)


def show_station_admin_view():
    station_id = st.session_state.station_id

    announcements = db.get_active_announcements()
    for ann in announcements:
        st.markdown(
            f'<div class="alert-info">📢 {ann["title"]}: {ann["message"]}</div>',
            unsafe_allow_html=True
        )

    tabs = st.tabs([
        "🏪 Dashboard",
        "🔍 Verify Token",
        "📊 Analytics",
        "🔧 Pump Management",
        "📦 Inventory"
    ])

    with tabs[0]:
        show_station_dashboard(db, station_id)

    with tabs[1]:
        show_verify_token(db, station_id)

    with tabs[2]:
        show_station_analytics(db, station_id)

    with tabs[3]:
        show_pump_management(db, station_id)

    with tabs[4]:
        show_inventory_management(db, station_id)


def show_govt_segment():
    with st.sidebar:
        st.markdown(f"### 🏛️ {st.session_state.user_name}")
        st.caption("Role: Government Official")
        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("⛽ Fuel", use_container_width=True,
                         type="primary" if st.session_state.govt_view == "fuel"
                         else "secondary"):
                st.session_state.govt_view = "fuel"
                st.rerun()
        with col_b:
            if st.button("⚡ Elec", use_container_width=True,
                         type="primary" if st.session_state.govt_view == "electricity"
                         else "secondary"):
                st.session_state.govt_view = "electricity"
                st.rerun()

        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            logout_user()
            st.rerun()

    if st.session_state.get("force_pw_change"):
        show_force_password_change()
        return

    govt_view = st.session_state.govt_view

    if govt_view is None:
        st.markdown("## 🏛️ Government Control Panel")
        st.markdown(f"Welcome, **{st.session_state.user_name}**")
        st.markdown("---")
        st.markdown("### Select your working area:")
        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown("""
            <div class="segment-card">
                <div style="font-size:50px">⛽</div>
                <h2 style="color:#00C853">Fuel Management</h2>
                <p style="color:#B0BEC5">
                National analytics, quotas, prices, special vehicles,
                announcements, audit log.
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Fuel Management →", key="govt_fuel",
                         use_container_width=True):
                st.session_state.govt_view = "fuel"
                st.rerun()

        with col2:
            st.markdown("""
            <div class="segment-card">
                <div style="font-size:50px">⚡</div>
                <h2 style="color:#1E90FF">Electricity Management</h2>
                <p style="color:#B0BEC5">
                Outage analytics by area, feeder performance,
                PDB activity audit log.
                </p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open Electricity Management →", key="govt_elec",
                         use_container_width=True):
                st.session_state.govt_view = "electricity"
                st.rerun()

    elif govt_view == "fuel":
        show_govt_control_panel(db, section="fuel")

    elif govt_view == "electricity":
        show_govt_control_panel(db, section="electricity")

def show_force_password_change():
    st.markdown("## 🔐 Password Change Required")
    st.markdown(
        '<div class="alert-warning">Your password has been reset. '
        'Please create a new password to continue.</div>',
        unsafe_allow_html=True
    )
    st.markdown("")

    with st.form("force_pw_form"):
        new_pw  = st.text_input("New Password", type="password")
        conf_pw = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Save New Password",
                                          use_container_width=True)

        if submitted:
            if not new_pw or not conf_pw:
                st.error("Please fill in both fields.")
            elif new_pw != conf_pw:
                st.error("Passwords do not match.")
            elif len(new_pw) < 8:
                st.error("Password must be at least 8 characters.")
            elif not any(c.isupper() for c in new_pw):
                st.error("Password must contain at least one uppercase letter.")
            elif not any(c.islower() for c in new_pw):
                st.error("Password must contain at least one lowercase letter.")
            elif not any(c.isdigit() for c in new_pw):
                st.error("Password must contain at least one number.")
            elif new_pw.upper().startswith("TEMP-"):
                st.error("New password cannot match the temporary password format.")
            else:
                db.change_password(st.session_state.user_id, new_pw)
                st.session_state.force_pw_change = False
                st.success("Password changed successfully. Welcome!")
                st.rerun()


def main():
    segment = st.session_state.current_segment
    role    = st.session_state.role if st.session_state.logged_in else None

    if st.session_state.logged_in and role == "government_official":
        show_govt_segment()
        return

    if st.session_state.logged_in and role == "pdb_admin":
        if segment != "electricity":
            st.session_state.current_segment = "electricity"
        show_electricity_segment()
        return

    if st.session_state.logged_in and role == "station_admin":
        if segment != "fuel":
            st.session_state.current_segment = "fuel"
        show_fuel_segment()
        return

    if segment == "landing":
        show_landing_page()
    elif segment == "electricity":
        show_electricity_segment()
    elif segment == "fuel":
        show_fuel_segment()
    else:
        show_landing_page()


if __name__ == "__main__":
    main()
