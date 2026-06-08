import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email:
        return True
    demo_email    = st.secrets.get("DEMO_EMAIL", "")
    demo_password = st.secrets.get("DEMO_APP_PASSWORD", "")

    if demo_email and to_email.lower() == demo_email.lower():

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = demo_email
            msg["To"]      = to_email
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(demo_email, demo_password)
                smtp.send_message(msg)

            return True

        except smtplib.SMTPAuthenticationError:

            print(f"[EMAIL ERROR] Gmail authentication failed. "
                  f"Check DEMO_APP_PASSWORD in Streamlit Secrets.")
            return True

        except Exception as e:

            print(f"[EMAIL ERROR] {type(e).__name__}: {e}")
            return True

    else:

        print(f"[MOCK EMAIL]")
        print(f"  To:      {to_email}")
        print(f"  Subject: {subject}")
        print(f"  ---")
        print(body)
        print(f"  ---")
        return True


def show_email_confirmation(to_email: str):

    if to_email:
        st.caption(f"📧 Confirmation sent to: {to_email}")

def send_registration_confirmation(to_email: str, full_name: str,
                                    driver_license: str) -> bool:
    subject = "Welcome to Cholar Shongi"
    body = f"""
Welcome to Cholar Shongi, {full_name}.

Your account has been created successfully.

Driver's License: {driver_license}
Email: {to_email}

You can now book fuel appointments and
check electricity schedules.

If you did not create this account,
please ignore this email.

— Cholar Shongi Team
"""
    return send_email(to_email, subject, body.strip())


def send_booking_confirmation(to_email: str, full_name: str,
                               token: str, station_name: str,
                               station_address: str, slot_datetime: str,
                               fuel_type: str, amount: float,
                               price_per_litre: float,
                               estimated_cost: float,
                               vehicle_type: str,
                               license_plate: str) -> bool:
    subject = f"Booking Confirmed — Token {token}"


    try:
        slot_dt   = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str  = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        exp_date  = slot_dt.strftime("%B %d, %Y")
    except Exception:
        slot_str = slot_datetime
        exp_date = "midnight tonight"

    body = f"""
Dear {full_name},

Your fuel appointment has been confirmed.

Token:          {token}
Station:        {station_name}
Address:        {station_address}
Date & Time:    {slot_str}
Fuel Type:      {fuel_type}
Amount:         {int(amount)}L
Est. Cost:      ৳{estimated_cost:,.2f} (at ৳{price_per_litre}/L)
Vehicle:        {vehicle_type}
Plate:          {license_plate}

Show your token to the station operator when you arrive.

Your token expires at midnight on {exp_date}.
If you need to postpone or cancel, please use
Find My Booking on the Cholar Shongi app.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_walkin_submitted(to_email: str, full_name: str,
                           station_name: str, fuel_type: str,
                           vehicle_type: str,
                           submitted_at: str) -> bool:
    subject = "Walk-In Request Submitted — Cholar Shongi"
    body = f"""
Dear {full_name},

Your walk-in booking request has been submitted.

Station:    {station_name}
Fuel Type:  {fuel_type}
Vehicle:    {vehicle_type}
Submitted:  {submitted_at}

The station admin will review your request shortly.
You will receive another email when a decision is made.

You can check the status anytime using
Find My Booking on the Cholar Shongi app.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_walkin_approved(to_email: str, full_name: str,
                          token: str, station_name: str,
                          approved_at: str, fuel_type: str,
                          amount: float, price_per_litre: float,
                          estimated_cost: float,
                          vehicle_type: str,
                          license_plate: str) -> bool:
    subject = f"Walk-In Approved — Token {token}"
    body = f"""
Dear {full_name},

Your walk-in request has been approved.

Token:        {token}
Station:      {station_name}
Approved At:  {approved_at}
Fuel Type:    {fuel_type}
Amount:       {int(amount)}L
Est. Cost:    ৳{estimated_cost:,.2f} (at ৳{price_per_litre}/L)
Vehicle:      {vehicle_type}
Plate:        {license_plate}

Please proceed to the service counter immediately
and show this token to the station operator.

Your token is valid until midnight today.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_walkin_denied(to_email: str, full_name: str,
                        station_name: str, reason: str) -> bool:
    subject = "Walk-In Request Update — Cholar Shongi"
    body = f"""
Dear {full_name},

Your walk-in request at {station_name}
could not be accommodated at this time.

Reason: {reason}

You are welcome to:
  → Try another nearby station
  → Make an advance booking for a future slot

No penalty has been applied to your account.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_postponement_confirmed(to_email: str, full_name: str,
                                 token: str, station_name: str,
                                 old_slot: str, new_slot: str,
                                 fuel_type: str, amount: float,
                                 postpones_used: int) -> bool:
    subject = f"Appointment Rescheduled — Token {token}"

    try:
        old_dt  = datetime.strptime(old_slot, "%Y-%m-%d %H:%M:%S")
        new_dt  = datetime.strptime(new_slot, "%Y-%m-%d %H:%M:%S")
        old_str = old_dt.strftime("%A, %B %d at %I:%M %p")
        new_str = new_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        old_str = old_slot
        new_str = new_slot

    body = f"""
Dear {full_name},

Your appointment has been rescheduled.

Token:          {token} (unchanged)
Station:        {station_name}
Original Time:  {old_str}
New Time:       {new_str}
Fuel:           {fuel_type}  |  {int(amount)}L

Please arrive at your new appointment time
and show your token as usual.

Postponements used this month: {postpones_used} of 3

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_postponement_waitlisted(to_email: str, full_name: str,
                                  token: str, station_name: str,
                                  original_slot: str,
                                  expires_in_days: int = 3) -> bool:
    subject = "Added to Postponement Waitlist — Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(original_slot, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        slot_str = original_slot

    body = f"""
Dear {full_name},

No slots were available at {station_name}
in the next 3 days for postponement.

You have been added to the postponement waitlist.

Original Booking:  {slot_str}
Token:             {token}
Waitlist Expires:  {expires_in_days} days from now

What happens next:
  → Your original booking stays active
  → If a slot opens, you will be notified
    with a time-limited offer to accept
  → If no slot opens within {expires_in_days} days,
    your booking is automatically cancelled
    with no penalty applied

You can cancel this waitlist request anytime
from Find My Booking.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_offer(to_email: str, full_name: str,
                         station_name: str, slot_datetime: str,
                         fuel_type: str, amount: float,
                         estimated_cost: float,
                         offer_window_minutes: int) -> bool:
    subject = "Slot Available — Action Required | Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        slot_str = slot_datetime

    body = f"""
Dear {full_name},

A slot has opened at {station_name}.

Slot Time:   {slot_str}
Fuel:        {fuel_type}  |  {int(amount)}L
Est. Cost:   ৳{estimated_cost:,.2f}

You have {offer_window_minutes} minutes to accept this offer.

Please open the Cholar Shongi app and go to
Find My Booking to accept or decline.

If you do not respond within {offer_window_minutes} minutes,
the slot will be offered to the next person.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_offer_accepted(to_email: str, full_name: str,
                                  token: str, station_name: str,
                                  station_address: str,
                                  slot_datetime: str,
                                  fuel_type: str, amount: float,
                                  estimated_cost: float) -> bool:
    subject = f"Slot Confirmed — Token {token} | Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        exp_date = slot_dt.strftime("%B %d, %Y")
    except Exception:
        slot_str = slot_datetime
        exp_date = "midnight tonight"

    body = f"""
Dear {full_name},

Your waitlist slot has been confirmed.

Token:      {token}
Station:    {station_name}
Address:    {station_address}
Time:       {slot_str}
Fuel:       {fuel_type}  |  {int(amount)}L
Est. Cost:  ৳{estimated_cost:,.2f}

Show your token to the station operator when you arrive.
Token expires at midnight on {exp_date}.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_offer_declined(to_email: str, full_name: str,
                                  station_name: str) -> bool:
    subject = "Waitlist Offer Declined — Cholar Shongi"
    body = f"""
Dear {full_name},

You have declined the slot offer at {station_name}.

You have been removed from the waitlist.
You are welcome to join a new waitlist or
make a booking at another station.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_offer_expired(to_email: str, full_name: str,
                                 station_name: str) -> bool:
    subject = "Waitlist Offer Expired — Cholar Shongi"
    body = f"""
Dear {full_name},

Your waitlist offer for {station_name} has expired
as it was not accepted within the time window.

You have been removed from the waitlist.
You are welcome to join a new waitlist or
make a booking at another station.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_entry_expired(to_email: str, full_name: str,
                                 station_name: str) -> bool:
    subject = "Waitlist Entry Expired — Cholar Shongi"
    body = f"""
Dear {full_name},

No slot became available at {station_name}
within your waitlist period.

Your waitlist entry has been automatically removed.
No penalty has been applied to your account.

You are welcome to:
  → Try booking at another station
  → Join a new waitlist

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_waitlist_auto_removed(to_email: str, full_name: str,
                                station_name: str) -> bool:
    subject = "Removed from Waitlist — Cholar Shongi"
    body = f"""
Dear {full_name},

You have been removed from the waitlist at
{station_name} because you have made a
booking at another station.

No action is required from you.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_booking_cancelled_by_user(to_email: str, full_name: str,
                                    token: str, station_name: str,
                                    slot_datetime: str,
                                    penalty_message: str = "") -> bool:
    subject = "Booking Cancelled — Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        slot_str = slot_datetime

    penalty_section = ""
    if penalty_message:
        penalty_section = f"\nImportant: {penalty_message}\n"

    body = f"""
Dear {full_name},

Your booking has been cancelled.

Token:    {token} (now void)
Station:  {station_name}
Was for:  {slot_str}
{penalty_section}
If you need fuel, you are welcome to
make a new booking at any available station.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_booking_cancelled_by_system(to_email: str, full_name: str,
                                      token: str, station_name: str,
                                      slot_datetime: str,
                                      nearby_areas: list) -> bool:
    subject = "Appointment Cancelled — Station Notice | Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d at %I:%M %p")
    except Exception:
        slot_str = slot_datetime

    nearby_section = ""
    if nearby_areas:
        nearby_list   = "\n".join([f"  → {area}" for area in nearby_areas])
        nearby_section = f"\nNearby areas you may check:\n{nearby_list}\n"

    body = f"""
Dear {full_name},

We regret to inform you that your appointment
has been cancelled due to an unplanned
station closure.

Token:    {token} (now void)
Station:  {station_name}
Was for:  {slot_str}

No penalty has been applied to your account.
This cancellation was outside your control.
{nearby_section}
We apologise for the inconvenience.
Please make a new booking at another station.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_pump_closure_notification(to_email: str, full_name: str,
                                    token: str, station_name: str,
                                    slot_datetime: str,
                                    reassigned: bool = False,
                                    new_slot: str = None) -> bool:
    """
    Sent when a specific pump is emergency closed
    and a booking is affected.
    """
    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%I:%M %p")
    except Exception:
        slot_str = slot_datetime

    if reassigned and new_slot:
        try:
            new_dt  = datetime.strptime(new_slot, "%Y-%m-%d %H:%M:%S")
            new_str = new_dt.strftime("%I:%M %p")
        except Exception:
            new_str = new_slot

        subject = f"Appointment Rescheduled — Token {token}"
        body = f"""
Dear {full_name},

Your appointment at {station_name} has been
automatically rescheduled due to a pump issue.

Token:        {token} (unchanged)
Original:     {slot_str}
Rescheduled:  {new_str}

No action is required. Simply arrive at
your new appointment time as usual.

— Cholar Shongi
"""
    else:
        subject = f"Appointment Cancelled — Token {token}"
        body = f"""
Dear {full_name},

Your appointment at {station_name} (originally {slot_str})
has been cancelled due to an equipment issue.

Token:  {token} (now void)

No penalty has been applied to your account.
Please make a new booking at your convenience.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_service_receipt(to_email: str, full_name: str,
                          receipt_text: str) -> bool:
    subject = "Service Receipt — Cholar Shongi"
    body = f"""
Dear {full_name},

Your vehicle has been serviced.
Here is your receipt:

{receipt_text}

Thank you for using Cholar Shongi.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_no_show_warning(to_email: str, full_name: str,
                          slot_datetime: str,
                          station_name: str) -> bool:
    subject = "Missed Appointment Notice — Cholar Shongi"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        slot_str = slot_datetime

    body = f"""
Dear {full_name},

Your appointment on {slot_str}
at {station_name} was not serviced
before it expired.

This has been recorded as a missed
appointment on your account.

Note: A second missed appointment within
6 months will result in a temporary
booking restriction.

Please make sure to attend your booked
appointments or cancel in advance
to avoid restrictions.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_suspension_notice(to_email: str, full_name: str,
                            suspended_until: str,
                            reason: str) -> bool:
    subject = "Booking Access Restricted — Cholar Shongi"

    try:
        until_dt  = datetime.strptime(suspended_until, "%Y-%m-%d %H:%M:%S")
        until_str = until_dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        until_str = suspended_until

    body = f"""
Dear {full_name},

Your booking access has been temporarily restricted.

Reason:             {reason}
Restricted Until:   {until_str}

During this period you cannot make
new fuel bookings. You can still:
  → Check electricity schedules
  → View your booking history
  → Use emergency services if applicable

Your restriction will lift automatically
on the date shown above.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_suspension_lifted(to_email: str, full_name: str) -> bool:
    subject = "Booking Access Restored — Cholar Shongi"
    body = f"""
Dear {full_name},

Your booking access restriction has been
reviewed and lifted by the relevant authority.

Your account is now fully active.
You may make new bookings immediately.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())


def send_emergency_token(to_email: str, driver_name: str,
                          token: str, reg_number: str,
                          organisation: str, station_name: str,
                          station_address: str, fuel_type: str,
                          amount: float, eta_datetime: str) -> bool:
    subject = f"Emergency Service Authorised — {token}"

    try:
        eta_dt  = datetime.strptime(eta_datetime, "%Y-%m-%d %H:%M:%S")
        eta_str = eta_dt.strftime("%I:%M %p")
    except Exception:
        eta_str = eta_datetime

    body = f"""
Emergency fuel service has been authorised.

Token:        {token}
Vehicle:      {reg_number}
Organisation: {organisation}
Station:      {station_name}
Address:      {station_address}
Fuel:         {fuel_type}
Requested:    {int(amount)}L
ETA:          {eta_str}

Proceed to the station immediately and
show this token to the operator.
The station has been notified of your arrival.

Token valid until midnight today.

— Cholar Shongi Emergency Services
"""
    return send_email(to_email, subject, body.strip())


def send_password_reset_notification(to_email: str, full_name: str,
                                      temp_password: str) -> bool:
    """
    In a real system this would be sent automatically.
    In our system the govt official sees the temp password
    on screen and communicates it manually.
    This function is a placeholder for production use.
    """
    subject = "Password Reset — Cholar Shongi"
    body = f"""
Dear {full_name},

Your account password has been reset
by the system administrator.

Temporary Password: {temp_password}

Please log in with this temporary password
and change it immediately.

— Cholar Shongi
"""
    return send_email(to_email, subject, body.strip())
