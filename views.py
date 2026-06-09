import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date

from utils import (
    VEHICLE_TYPES, FUEL_TYPES, SLOT_DURATIONS,
    BOOKING_PURPOSES, FUEL_COLOURS, HEALTH_LABELS,
    HEALTH_COLOURS, STATUS_LABELS, STATUS_COLOURS,
    WALKIN_DENIAL_REASONS, FUEL_SUPPLIERS,
    ETA_OPTIONS, EMERGENCY_CATEGORY_LABELS,
    get_cities, get_areas, get_fuel_gauge_colour,
    get_fuel_pct, get_slot_duration, mask_token,
    format_datetime, format_time_only, format_date_only,
    format_duration, format_currency, format_currency_int,
    get_schedule_status, get_schedule_status_label,
    calculate_cost, generate_receipt_text,
    generate_emergency_receipt_text,
    get_slot_hold_deadline, is_slot_hold_valid,
    is_slot_late, is_slot_expired,
    get_eta_datetime, get_waitlist_offer_window,
    validate_driver_license, validate_license_plate,
    validate_emergency_registration, validate_fuel_amount,
    validate_dispensed_amount, validate_resupply_amount,
    validate_fuel_price, validate_eta_minutes,
    validate_announcement, validate_schedule,
    generate_token, generate_emergency_token,
    generate_temp_password, get_default_expiry_date,
    format_suspension_message, get_booking_type_label,
    get_adjacent_areas, CITIES_AREAS,
    format_walkin_denial_reason,
)
from auth import (
    require_role, get_active_suspension_message,
    check_late_cancellation, apply_cancellation_ban,
)
from email_service import (
    send_email, show_email_confirmation,
    send_registration_confirmation,
    send_booking_confirmation,
    send_walkin_submitted, send_walkin_approved,
    send_walkin_denied, send_postponement_confirmed,
    send_postponement_waitlisted, send_waitlist_offer,
    send_waitlist_offer_accepted, send_waitlist_offer_declined,
    send_waitlist_auto_removed, send_booking_cancelled_by_user,
    send_booking_cancelled_by_system,
    send_pump_closure_notification,
    send_service_receipt, send_no_show_warning,
    send_suspension_notice, send_suspension_lifted,
    send_emergency_token, send_password_reset_notification,
    send_waitlist_entry_expired,
)


def fuel_gauge_bar(label: str, stock: float,
                   capacity: float, fuel_type: str):
    pct    = get_fuel_pct(stock, capacity)
    colour = get_fuel_gauge_colour(stock, capacity)
    st.markdown(f"**{label}**")
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <div style="flex:1;background:#0A1628;border-radius:8px;
                        height:14px;overflow:hidden">
                <div style="width:{pct}%;background:{colour};
                            height:100%;border-radius:8px;
                            transition:width 0.5s"></div>
            </div>
            <span style="color:{colour};font-weight:bold;
                         min-width:60px;text-align:right">
                {pct}%
            </span>
            <span style="color:#B0BEC5;font-size:0.85rem;min-width:120px">
                {int(stock)}L / {int(capacity)}L
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )


def token_card(token: str, station_name: str, station_address: str,
               slot_datetime: str, fuel_type: str, amount: float,
               estimated_cost: float, expires_label: str,
               is_emergency: bool = False):
    colour = "#FF3D00" if is_emergency else "#1E90FF"
    label  = "🚨 EMERGENCY TOKEN" if is_emergency else "✅ Booking Confirmed!"

    try:
        slot_dt  = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M:%S")
        slot_str = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        slot_str = slot_datetime

    st.markdown(
        f"""
        <div style="background:#132039;border:2px solid {colour};
                    border-radius:16px;padding:28px;text-align:center;
                    margin:16px 0">
            <div style="font-size:1.1rem;color:#B0BEC5;
                        margin-bottom:8px">{label}</div>
            <div style="font-family:monospace;font-size:2.2rem;
                        font-weight:900;color:{colour};
                        letter-spacing:6px;margin:12px 0">
                {token}
            </div>
            <hr style="border-color:{colour}33;margin:16px 0">
            <div style="text-align:left;color:#FFFFFF;
                        line-height:2;font-size:0.95rem">
                <b>Station:</b>    {station_name}<br>
                <b>Address:</b>    {station_address}<br>
                <b>Time:</b>       {slot_str}<br>
                <b>Fuel:</b>       {fuel_type} | {int(amount)}L<br>
                <b>Est. Cost:</b>  {format_currency(estimated_cost)}<br>
                <b>Expires:</b>    {expires_label}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.button("📋 Copy Token", key=f"copy_{token}",
              help=f"Token: {token}")


def status_badge(status: str) -> str:
    label  = STATUS_LABELS.get(status, status.title())
    colour = STATUS_COLOURS.get(status, "#B0BEC5")
    return (
        f'<span style="background:{colour}22;color:{colour};'
        f'padding:3px 10px;border-radius:20px;font-size:0.8rem;'
        f'border:1px solid {colour}">{label}</span>'
    )


def health_badge(health: str) -> str:
    label  = HEALTH_LABELS.get(health, health)
    colour = HEALTH_COLOURS.get(health, "#B0BEC5")
    return (
        f'<span style="background:{colour}22;color:{colour};'
        f'padding:4px 14px;border-radius:20px;font-size:0.9rem;'
        f'border:1px solid {colour};font-weight:bold">{label}</span>'
    )


def period_selector(key: str = "period") -> str:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("This Week",  key=f"{key}_week",
                     use_container_width=True):
            st.session_state[f"{key}_selected"] = "week"
    with col2:
        if st.button("This Month", key=f"{key}_month",
                     use_container_width=True):
            st.session_state[f"{key}_selected"] = "month"
    with col3:
        if st.button("This Year",  key=f"{key}_year",
                     use_container_width=True):
            st.session_state[f"{key}_selected"] = "year"
    return st.session_state.get(f"{key}_selected", "week")


def show_electricity_public(db):
    st.markdown("## ⚡ Electricity Schedules")
    st.markdown(
        '<p style="color:#B0BEC5">Check load shedding schedules '
        'for your area. No login required.</p>',
        unsafe_allow_html=True
    )

    for ann in db.get_active_announcements():
        st.markdown(
            f'<div style="background:#1E90FF15;border-left:4px solid #1E90FF;'
            f'padding:10px 16px;border-radius:8px;margin:8px 0">'
            f'📢 <strong>{ann["title"]}</strong>: {ann["message"]}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        city = st.selectbox("Select City", [""] + get_cities(),
                            key="elec_city")
    with col2:
        areas = get_areas(city) if city else []
        area  = st.selectbox("Select Area",
                             [""] + areas if areas else [""],
                             key="elec_area")

    if not city or not area:
        st.info("Please select a city and area to view schedules.")
        return

    if db.check_48hr_change(city, area):
        st.markdown(
            f'<div style="background:#FFB30015;border-left:4px solid '
            f'#FFB300;padding:10px 16px;border-radius:8px;margin:8px 0">'
            f'⚠️ Schedules in <strong>{area}</strong> have been updated '
            f'in the last 48 hours.</div>',
            unsafe_allow_html=True
        )

    schedules = db.get_schedules_for_area(city, area)

    if not schedules:
        st.info(f"No schedules found for {area}, {city}.")
        return

    active   = [s for s in schedules
                if get_schedule_status(s["start_datetime"],
                                       s["end_datetime"]) == "active"]
    upcoming = [s for s in schedules
                if get_schedule_status(s["start_datetime"],
                                       s["end_datetime"]) == "upcoming"]
    expired  = [s for s in schedules
                if get_schedule_status(s["start_datetime"],
                                       s["end_datetime"]) == "expired"]

    def schedule_card(s, colour):
        start_str = format_datetime(s["start_datetime"])
        end_str   = format_time_only(s["end_datetime"])
        duration  = format_duration(s["start_datetime"], s["end_datetime"])
        st.markdown(
            f'<div style="background:#132039;border-left:4px solid {colour};'
            f'padding:16px;border-radius:8px;margin:8px 0">'
            f'<strong>{s["feeder_name"]}</strong><br>'
            f'<span style="color:#B0BEC5">Start: {start_str}</span><br>'
            f'<span style="color:#B0BEC5">End:   {end_str}</span><br>'
            f'<span style="color:{colour}">Duration: {duration}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    if active:
        st.markdown("### ⚡ Active Now")
        for s in active:
            schedule_card(s, "#FF3D00")

    if upcoming:
        st.markdown("### 🕐 Upcoming")
        for s in upcoming:
            schedule_card(s, "#FFB300")

    if expired:
        with st.expander(f"✅ Expired ({len(expired)} schedules)"):
            for s in expired:
                schedule_card(s, "#B0BEC5")

    if not active and not upcoming:
        st.success(f"No active or upcoming power cuts scheduled "
                   f"for {area} in the next 7 days.")


@require_role("pdb_admin")
def show_pdb_dashboard(db):
    city = st.session_state.assigned_city
    st.markdown(f"## ⚡ PDB Command Center — {city}")

    tabs = st.tabs(["📢 Publish", "📋 Manage", "📜 History"])

    with tabs[0]:
        st.markdown("### Publish New Schedule")
        feeders = db.get_feeders_for_city(city)
        if not feeders:
            st.warning("No feeders found for your city.")
            return

        feeder_options = {f"{f['name']} ({f['area']})": f["id"]
                          for f in feeders}

        with st.form("publish_schedule_form"):
            feeder_label = st.selectbox(
                "Feeder Line", list(feeder_options.keys())
            )
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date",
                                            min_value=date.today())
                start_time = st.time_input("Start Time")
            with col2:
                end_date   = st.date_input("End Date",
                                            min_value=date.today())
                end_time   = st.time_input("End Time")
            note      = st.text_area(
                "Internal Note (optional, not shown to public)",
                max_chars=500
            )
            submitted = st.form_submit_button("📢 Publish Schedule",
                                               use_container_width=True)

            if submitted:
                start_dt   = datetime.combine(start_date, start_time)
                end_dt     = datetime.combine(end_date,   end_time)
                valid, msg = validate_schedule(start_dt, end_dt)
                if not valid:
                    st.error(msg)
                else:
                    feeder_id = feeder_options[feeder_label]
                    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                    end_str   = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                    db.publish_schedule(
                        feeder_id, start_str, end_str,
                        note, st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        "Published schedule",
                        f"{feeder_label} — "
                        f"{start_dt.strftime('%b %d %H:%M')} to "
                        f"{end_dt.strftime('%H:%M')}",
                        "electricity"
                    )
                    st.success("✅ Schedule published successfully.")
                    st.rerun()

    with tabs[1]:
        st.markdown("### Manage Existing Schedules")
        schedules = db.get_all_schedules_for_city(city)

        if not schedules:
            st.info("No schedules found.")
        else:
            for s in schedules:
                status     = get_schedule_status(s["start_datetime"],
                                                  s["end_datetime"])
                colour_map = {
                    "active":   "#FF3D00",
                    "upcoming": "#FFB300",
                    "expired":  "#B0BEC5",
                }
                colour = colour_map.get(status, "#B0BEC5")

                with st.expander(
                    f"{s['feeder_name']} — "
                    f"{format_date_only(s['start_datetime'])} "
                    f"{get_schedule_status_label(status)}"
                ):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(
                            f"**Start:** {format_datetime(s['start_datetime'])}  \n"
                            f"**End:** {format_datetime(s['end_datetime'])}  \n"
                            f"**Duration:** {format_duration(s['start_datetime'], s['end_datetime'])}"
                        )
                        if s["internal_note"]:
                            st.caption(f"Note: {s['internal_note']}")
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_{s['id']}"):
                            db.delete_schedule(s["id"])
                            db.log_audit(
                                st.session_state.user_id,
                                "Deleted schedule",
                                f"{s['feeder_name']} — deleted",
                                "electricity"
                            )
                            st.success("Schedule deleted.")
                            st.rerun()

                    with st.form(f"edit_form_{s['id']}"):
                        st.markdown("**Edit Schedule:**")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            e_start_date = st.date_input(
                                "New Start Date",
                                value=datetime.strptime(
                                    s["start_datetime"],
                                    "%Y-%m-%d %H:%M:%S"
                                ).date(),
                                key=f"esd_{s['id']}"
                            )
                            e_start_time = st.time_input(
                                "New Start Time",
                                value=datetime.strptime(
                                    s["start_datetime"],
                                    "%Y-%m-%d %H:%M:%S"
                                ).time(),
                                key=f"est_{s['id']}"
                            )
                        with ec2:
                            e_end_date = st.date_input(
                                "New End Date",
                                value=datetime.strptime(
                                    s["end_datetime"],
                                    "%Y-%m-%d %H:%M:%S"
                                ).date(),
                                key=f"eed_{s['id']}"
                            )
                            e_end_time = st.time_input(
                                "New End Time",
                                value=datetime.strptime(
                                    s["end_datetime"],
                                    "%Y-%m-%d %H:%M:%S"
                                ).time(),
                                key=f"eet_{s['id']}"
                            )
                        e_note = st.text_area(
                            "Note", value=s["internal_note"] or "",
                            key=f"en_{s['id']}"
                        )
                        if st.form_submit_button("💾 Save Changes"):
                            new_start  = datetime.combine(e_start_date,
                                                           e_start_time)
                            new_end    = datetime.combine(e_end_date,
                                                           e_end_time)
                            valid, msg = validate_schedule(new_start, new_end)
                            if not valid:
                                st.error(msg)
                            else:
                                db.update_schedule(
                                    s["id"],
                                    new_start.strftime("%Y-%m-%d %H:%M:%S"),
                                    new_end.strftime("%Y-%m-%d %H:%M:%S"),
                                    e_note
                                )
                                db.log_audit(
                                    st.session_state.user_id,
                                    "Edited schedule",
                                    f"{s['feeder_name']} — updated times",
                                    "electricity"
                                )
                                st.success("Schedule updated.")
                                st.rerun()

        st.markdown("---")
        if st.button("🗑️ Clear All Expired Schedules",
                     use_container_width=True):
            count = db.delete_expired_schedules(city)
            db.log_audit(
                st.session_state.user_id,
                "Bulk deleted expired schedules",
                f"{count} expired schedules removed",
                "electricity"
            )
            st.success(f"Cleared {count} expired schedule(s).")
            st.rerun()

    with tabs[2]:
        st.markdown("### Schedule History")
        all_schedules = db.get_all_schedules_for_city(city)
        if not all_schedules:
            st.info("No schedule history.")
            return

        rows = []
        for s in all_schedules:
            status = get_schedule_status(s["start_datetime"],
                                          s["end_datetime"])
            rows.append({
                "Feeder":   s["feeder_name"],
                "Area":     s["area"],
                "Start":    format_datetime(s["start_datetime"]),
                "End":      format_time_only(s["end_datetime"]),
                "Duration": format_duration(s["start_datetime"],
                                             s["end_datetime"]),
                "Status":   get_schedule_status_label(status),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


def show_advance_booking(db):
    st.markdown("## 📅 Advance Booking")

    if "booking_step" not in st.session_state:
        st.session_state.booking_step = 1

    step = st.session_state.booking_step

    steps         = ["Location", "Vehicle & Fuel",
                     "Slot", "Details", "Confirm", "Done"]
    progress_html = ""
    for i, s_label in enumerate(steps, 1):
        colour = "#1E90FF" if i == step else (
            "#00C853" if i < step else "#B0BEC530"
        )
        progress_html += (
            f'<span style="color:{colour};margin:0 8px;'
            f'font-size:0.85rem">{"●" if i <= step else "○"} {s_label}</span>'
        )
    st.markdown(
        f'<div style="margin-bottom:16px">{progress_html}</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    if step == 1:
        st.markdown("### Step 1: Select Location")
        col1, col2 = st.columns(2)
        with col1:
            city = st.selectbox("City", [""] + get_cities(),
                                key="adv_city")
        with col2:
            areas = get_areas(city) if city else []
            area  = st.selectbox("Area",
                                 [""] + areas if areas else [""],
                                 key="adv_area")

        if city and area:
            stations = db.get_stations_by_area(city, area)
            if not stations:
                st.warning("No stations found in this area.")
                return

            st.markdown("**Available Stations:**")
            for stn in stations:
                st.markdown(
                    f'<div style="background:#132039;padding:12px 16px;'
                    f'border-radius:8px;margin:6px 0;'
                    f'border:1px solid #1E90FF22">'
                    f'<strong>{stn["name"]}</strong><br>'
                    f'<span style="color:#B0BEC5;font-size:0.85rem">'
                    f'{stn["address"]}</span><br>'
                    f'<span style="color:#B0BEC5;font-size:0.85rem">'
                    f'Opens {stn["opening_time"]} — '
                    f'Closes {stn["closing_time"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button(f"Select {stn['name']}",
                             key=f"sel_stn_{stn['id']}",
                             use_container_width=True):
                    st.session_state.selected_city    = city
                    st.session_state.selected_area    = area
                    st.session_state.selected_station = dict(stn)
                    st.session_state.booking_step     = 2
                    st.rerun()

    elif step == 2:
        stn = st.session_state.selected_station
        st.markdown("### Step 2: Vehicle & Fuel")
        st.markdown(
            f'<div style="color:#B0BEC5;margin-bottom:8px">'
            f'Station: <strong>{stn["name"]}</strong></div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            vehicle = st.selectbox("Vehicle Type", VEHICLE_TYPES,
                                   key="adv_vehicle")
        with col2:
            fuel = st.selectbox("Fuel Type", FUEL_TYPES,
                                key="adv_fuel")

        available = db.get_available_fuel(stn["id"], fuel)
        is_open   = db.is_fuel_open(stn["id"], fuel)

        if not is_open:
            st.error(
                f"Appointments currently closed for {fuel} "
                f"at this station."
            )
        else:
            daily_limit = db.get_daily_limit(vehicle, fuel)
            price       = db.get_fuel_price(fuel)

            st.info(
                f"Daily limit for {vehicle} + {fuel}: "
                f"**{int(daily_limit)}L maximum**"
            )

            amount = st.number_input(
                "How many litres do you need?",
                min_value=1,
                max_value=int(daily_limit),
                value=min(int(daily_limit), 40),
                step=1,
                key="adv_amount"
            )

            est_cost = calculate_cost(amount, price)
            st.markdown(
                f'<div style="background:#132039;padding:12px;'
                f'border-radius:8px;margin:8px 0">'
                f'Current price: <strong>{format_currency(price)}/L</strong>'
                f'&nbsp;&nbsp;|&nbsp;&nbsp;'
                f'Estimated cost: <strong>{format_currency(est_cost)}</strong>'
                f'</div>',
                unsafe_allow_html=True
            )

            col_back, col_next = st.columns(2)
            with col_back:
                if st.button("← Back", use_container_width=True):
                    st.session_state.booking_step = 1
                    st.rerun()
            with col_next:
                if st.button("Continue →", use_container_width=True,
                             type="primary"):
                    valid, msg = validate_fuel_amount(
                        amount, daily_limit, available
                    )
                    if not valid:
                        st.error(msg)
                    else:
                        st.session_state.selected_vehicle = vehicle
                        st.session_state.selected_fuel    = fuel
                        st.session_state.requested_amount = amount
                        st.session_state.booking_step     = 3
                        st.rerun()

    elif step == 3:
        stn     = st.session_state.selected_station
        vehicle = st.session_state.selected_vehicle
        fuel    = st.session_state.selected_fuel
        amount  = st.session_state.requested_amount

        st.markdown("### Step 3: Select Time Slot")
        st.markdown(
            f'<div style="color:#B0BEC5;margin-bottom:8px">'
            f'{stn["name"]} · {vehicle} · {fuel} · {int(amount)}L'
            f'</div>',
            unsafe_allow_html=True
        )

        hold_deadline = st.session_state.get("slot_hold_until")
        if hold_deadline and is_slot_hold_valid(hold_deadline):
            st.session_state.booking_step = 4
            st.rerun()

        today_slots = db.get_available_slots(stn["id"], date.today(), vehicle)
        best_slot   = today_slots[0] if today_slots else None

        if best_slot:
            best_str = best_slot.strftime("%A, %B %d at %I:%M %p")
            st.markdown(
                f'<div style="background:#00C85315;border:2px solid #00C853;'
                f'padding:16px;border-radius:12px;margin:8px 0;'
                f'text-align:center">'
                f'<div style="color:#B0BEC5;font-size:0.85rem">⭐ BEST AVAILABLE</div>'
                f'<div style="font-size:1.2rem;color:#FFFFFF;font-weight:bold;'
                f'margin:8px 0">{best_str}</div>'
                f'<div style="color:#B0BEC5;font-size:0.85rem">'
                f'First available slot at least 30 minutes from now</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            col_best, col_browse = st.columns(2)
            with col_best:
                if st.button("✅ Book This Slot",
                             use_container_width=True, type="primary"):
                    st.session_state.selected_slot   = best_slot.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    st.session_state.slot_hold_until = get_slot_hold_deadline(10)
                    st.session_state.booking_step    = 4
                    st.rerun()
            with col_browse:
                if st.button("📅 Browse All Slots", use_container_width=True):
                    st.session_state["show_full_grid"] = True
                    st.rerun()
        else:
            st.session_state["show_full_grid"] = True

        if st.session_state.get("show_full_grid"):
            st.markdown("#### Available Slots")
            for days_ahead in range(3):
                target_date = date.today() + timedelta(days=days_ahead)
                label = (
                    "Today" if days_ahead == 0
                    else "Tomorrow" if days_ahead == 1
                    else target_date.strftime("%A, %B %d")
                )
                slots = db.get_available_slots(
                    stn["id"], target_date, vehicle
                )
                st.markdown(f"**{label}**")
                if not slots:
                    st.caption("No available slots")
                    continue

                cols = st.columns(3)
                for idx, slot in enumerate(slots):
                    with cols[idx % 3]:
                        slot_str = slot.strftime("%Y-%m-%d %H:%M:%S")
                        time_str = slot.strftime("%I:%M %p")
                        if st.button(time_str,
                                     key=f"slot_{slot_str}",
                                     use_container_width=True):
                            st.session_state.selected_slot   = slot_str
                            st.session_state.slot_hold_until = get_slot_hold_deadline(10)
                            st.session_state.show_full_grid  = False
                            st.session_state.booking_step    = 4
                            st.rerun()

            all_empty = all(
                not db.get_available_slots(
                    stn["id"],
                    date.today() + timedelta(days=d), vehicle
                )
                for d in range(3)
            )
            if all_empty:
                st.markdown("---")
                st.markdown(
                    '<div style="background:#FFB30015;border:1px solid #FFB300;'
                    'padding:16px;border-radius:12px;text-align:center">'
                    '⚠️ No slots available in the next 3 days.'
                    '</div>',
                    unsafe_allow_html=True
                )
                if st.button("📋 Join Waitlist",
                             use_container_width=True, type="primary"):
                    wl_id = db.join_waitlist(
                        st.session_state.user_id,
                        stn["id"], fuel, vehicle,
                        st.session_state.get("adv_plate", ""),
                        amount, "advance", None, 0
                    )
                    if wl_id:
                        pos = db.get_waitlist_position(wl_id)
                        st.success(
                            f"You have joined the waitlist for {stn['name']}. "
                            f"You are approximately #{pos} in the queue. "
                            f"You will be notified when a slot opens."
                        )
                        show_email_confirmation(st.session_state.email)
                        st.session_state.booking_step = 1
                    else:
                        st.warning(
                            "You already have an active waitlist entry "
                            "for this station."
                        )

        if st.button("← Back to Vehicle/Fuel", use_container_width=True):
            st.session_state.booking_step   = 2
            st.session_state.show_full_grid = False
            st.rerun()

    elif step == 4:
        stn        = st.session_state.selected_station
        vehicle    = st.session_state.selected_vehicle
        fuel       = st.session_state.selected_fuel
        amount     = st.session_state.requested_amount
        slot_str   = st.session_state.selected_slot
        hold_until = st.session_state.get("slot_hold_until", "")

        st.markdown("### Step 4: Your Details")

        try:
            slot_dt   = datetime.strptime(slot_str, "%Y-%m-%d %H:%M:%S")
            slot_disp = slot_dt.strftime("%A, %B %d at %I:%M %p")
        except Exception:
            slot_disp = slot_str

        st.markdown(
            f'<div style="background:#132039;padding:12px;'
            f'border-radius:8px;margin-bottom:12px">'
            f'Selected slot: <strong>{slot_disp}</strong>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'⏱️ Slot held until <strong>{hold_until}</strong>'
            f'</div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name",
                          value=st.session_state.user_name,
                          disabled=True, key="adv_name_display")
        with col2:
            st.text_input("Email",
                          value=st.session_state.email,
                          disabled=True, key="adv_email_display")

        st.text_input("Driver's License",
                      value=st.session_state.driver_license,
                      disabled=True, key="adv_dl_display")

        plate = st.text_input(
            "License Plate",
            placeholder=(
                "RS-DHAKA-KA-05-1122"
                if "Ride Share" in vehicle
                else "DHAKA-METRO-GA-11-2233"
            ),
            key="adv_plate"
        )
        purpose = st.selectbox(
            "Booking Purpose (optional)",
            [""] + BOOKING_PURPOSES,
            key="adv_purpose"
        )

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Back", use_container_width=True):
                st.session_state.booking_step = 3
                st.rerun()
        with col_next:
            if st.button("Continue →", use_container_width=True,
                         type="primary"):
                if not is_slot_hold_valid(hold_until):
                    st.error(
                        "Your slot hold has expired. "
                        "Please select a new slot."
                    )
                    st.session_state.slot_hold_until = None
                    st.session_state.booking_step    = 3
                    st.rerun()

                if not plate:
                    st.error("Please enter your license plate.")
                    st.stop()

                valid, cleaned_plate = validate_license_plate(
                    plate, vehicle
                )
                if not valid:
                    st.error(cleaned_plate)
                    st.stop()

                errors = db.validate_booking_request(
                    stn["id"], vehicle, fuel,
                    cleaned_plate,
                    st.session_state.driver_license,
                    amount
                )
                if errors:
                    for e in errors:
                        st.error(e)
                    st.stop()

                st.session_state.adv_plate_cleaned = cleaned_plate
                st.session_state.adv_purpose_val   = (
                    purpose if purpose else None
                )
                st.session_state.booking_step      = 5
                st.rerun()

    elif step == 5:
        stn      = st.session_state.selected_station
        vehicle  = st.session_state.selected_vehicle
        fuel     = st.session_state.selected_fuel
        amount   = st.session_state.requested_amount
        slot_str = st.session_state.selected_slot
        plate    = st.session_state.adv_plate_cleaned
        purpose  = st.session_state.adv_purpose_val
        price    = db.get_fuel_price(fuel)
        est      = calculate_cost(amount, price)

        st.markdown("### Step 5: Confirm Booking")
        st.markdown("Please review your booking details before confirming:")

        try:
            slot_dt   = datetime.strptime(slot_str, "%Y-%m-%d %H:%M:%S")
            slot_disp = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
            exp_label = f"Midnight, {slot_dt.strftime('%B %d, %Y')}"
        except Exception:
            slot_disp = slot_str
            exp_label = "Midnight tonight"

        st.markdown(
            f'<div style="background:#132039;border:1px solid #1E90FF44;'
            f'border-radius:12px;padding:20px;line-height:2.2">'
            f'<strong>Station:</strong>     {stn["name"]}<br>'
            f'<strong>Address:</strong>     {stn["address"]}<br>'
            f'<strong>Date & Time:</strong> {slot_disp}<br>'
            f'<strong>Fuel:</strong>        {fuel}<br>'
            f'<strong>Amount:</strong>      {int(amount)}L<br>'
            f'<strong>Vehicle:</strong>     {vehicle}<br>'
            f'<strong>Plate:</strong>       {plate}<br>'
            f'<strong>Est. Cost:</strong>   {format_currency(est)} '
            f'(at {format_currency(price)}/L)<br>'
            f'<strong>Purpose:</strong>     {purpose or "Not specified"}'
            f'</div>',
            unsafe_allow_html=True
        )

        col_edit, col_confirm = st.columns(2)
        with col_edit:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.booking_step = 4
                st.rerun()
        with col_confirm:
            if st.button("✅ Confirm Booking",
                         use_container_width=True, type="primary"):
                hold_until = st.session_state.get("slot_hold_until", "")
                if not is_slot_hold_valid(hold_until):
                    st.error("Slot hold expired. Please select a new slot.")
                    st.session_state.booking_step = 3
                    st.rerun()

                token = generate_token(db)
                db.create_booking(
                    token,
                    st.session_state.user_id,
                    stn["id"],
                    "advance",
                    vehicle, fuel, plate,
                    st.session_state.driver_license,
                    st.session_state.user_name,
                    st.session_state.email,
                    amount, price, slot_str, purpose
                )
                st.session_state.booking_token   = token
                st.session_state.booking_step    = 6
                st.session_state.slot_hold_until = None
                st.rerun()

    elif step == 6:
        stn      = st.session_state.selected_station
        vehicle  = st.session_state.selected_vehicle
        fuel     = st.session_state.selected_fuel
        amount   = st.session_state.requested_amount
        slot_str = st.session_state.selected_slot
        token    = st.session_state.booking_token
        price    = db.get_fuel_price(fuel)
        est      = calculate_cost(amount, price)

        try:
            slot_dt   = datetime.strptime(slot_str, "%Y-%m-%d %H:%M:%S")
            exp_label = f"Midnight, {slot_dt.strftime('%B %d, %Y')}"
        except Exception:
            exp_label = "Midnight tonight"

        token_card(
            token, stn["name"], stn["address"],
            slot_str, fuel, amount, est, exp_label
        )

        send_booking_confirmation(
            st.session_state.email,
            st.session_state.user_name,
            token, stn["name"], stn["address"],
            slot_str, fuel, amount, price, est,
            vehicle,
            st.session_state.get("adv_plate_cleaned", "")
        )
        show_email_confirmation(st.session_state.email)

        if st.button("Make Another Booking", use_container_width=True):
            for key in [
                "selected_city", "selected_area", "selected_station",
                "selected_vehicle", "selected_fuel", "requested_amount",
                "selected_slot", "booking_token", "adv_plate_cleaned",
                "adv_purpose_val"
            ]:
                st.session_state.pop(key, None)
            st.session_state.booking_step = 1
            st.rerun()


def show_walkin_booking(db):
    st.markdown("## 🚶 Walk-In Booking")
    st.markdown(
        '<p style="color:#B0BEC5">'
        'For when you are at a station and want to refuel now. '
        'Requires admin approval.</p>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        city = st.selectbox("City", [""] + get_cities(), key="wi_city")
    with col2:
        areas = get_areas(city) if city else []
        area  = st.selectbox("Area",
                             [""] + areas if areas else [""],
                             key="wi_area")

    if not city or not area:
        st.info("Please select your city and area.")
        return

    stations = db.get_stations_by_area(city, area)
    if not stations:
        st.warning("No stations found in this area.")
        return

    walkin_stations = [s for s in stations if s["walkin_enabled"]]
    closed_stations = [s for s in stations if not s["walkin_enabled"]]

    for s in closed_stations:
        st.markdown(
            f'<div style="background:#FF3D0010;border:1px solid #FF3D00;'
            f'padding:10px;border-radius:8px;margin:4px 0;color:#B0BEC5">'
            f'❌ {s["name"]} — Not accepting walk-in requests</div>',
            unsafe_allow_html=True
        )

    if not walkin_stations:
        st.warning("No stations in this area are currently accepting walk-ins.")
        return

    with st.form("walkin_form"):
        station_options = {s["name"]: s for s in walkin_stations}
        station_name    = st.selectbox(
            "Station (walk-ins enabled)",
            list(station_options.keys())
        )
        selected_stn = station_options[station_name]

        col1, col2 = st.columns(2)
        with col1:
            vehicle = st.selectbox("Vehicle Type", VEHICLE_TYPES,
                                   key="wi_vehicle")
        with col2:
            fuel = st.selectbox("Fuel Type", FUEL_TYPES, key="wi_fuel")

        daily_limit = db.get_daily_limit(vehicle, fuel)
        price       = db.get_fuel_price(fuel)
        is_open     = db.is_fuel_open(selected_stn["id"], fuel)

        if not is_open:
            st.error(f"Appointments currently closed for {fuel} "
                     f"at this station.")
        else:
            st.info(
                f"Daily limit: {int(daily_limit)}L  |  "
                f"Current price: {format_currency(price)}/L  |  "
                f"Note: Final price confirmed at admin approval time."
            )

            amount = st.number_input(
                "How many litres?",
                min_value=1,
                max_value=int(daily_limit),
                value=min(int(daily_limit), 40),
                step=1
            )
            est = calculate_cost(amount, price)
            st.caption(f"Estimated cost: {format_currency(est)}")

            plate = st.text_input(
                "License Plate",
                placeholder="DHAKA-METRO-GA-11-2233",
                key="wi_plate"
            )
            purpose = st.selectbox(
                "Booking Purpose (optional)",
                [""] + BOOKING_PURPOSES
            )

            submitted = st.form_submit_button(
                "Submit Walk-In Request", use_container_width=True,
                type="primary"
            )

            if submitted:
                if not plate:
                    st.error("Please enter your license plate.")
                    st.stop()

                valid, cleaned = validate_license_plate(plate, vehicle)
                if not valid:
                    st.error(cleaned)
                    st.stop()

                errors = db.validate_booking_request(
                    selected_stn["id"], vehicle, fuel,
                    cleaned, st.session_state.driver_license, amount
                )
                if errors:
                    for e in errors:
                        st.error(e)
                    st.stop()

                token = generate_token(db)
                db.create_walkin_request(
                    token,
                    st.session_state.user_id,
                    selected_stn["id"],
                    vehicle, fuel, cleaned,
                    st.session_state.driver_license,
                    st.session_state.user_name,
                    st.session_state.email,
                    amount, price
                )

                send_walkin_submitted(
                    st.session_state.email,
                    st.session_state.user_name,
                    selected_stn["name"], fuel, vehicle,
                    datetime.now().strftime("%I:%M %p, %B %d, %Y")
                )

                st.success(
                    "✅ Walk-in request submitted successfully! "
                    "The station admin will review your request."
                )
                show_email_confirmation(st.session_state.email)
                st.markdown(
                    '<div style="background:#132039;padding:12px;'
                    'border-radius:8px;margin-top:8px;color:#B0BEC5">'
                    'Your request is pending approval. '
                    'Check the status in Find My Booking.</div>',
                    unsafe_allow_html=True
                )


def show_emergency_services(db):
    st.markdown("## 🚨 Emergency Services")
    st.markdown(
        '<p style="color:#B0BEC5">'
        'Reserved for registered emergency and government vehicles. '
        'No login required.</p>',
        unsafe_allow_html=True
    )

    reg = st.text_input(
        "Enter Vehicle Registration Number",
        placeholder="FIRE-CTG-001 or AMB-DHK-001",
        key="emr_reg"
    ).strip().upper()

    if not reg:
        st.info("Enter your emergency vehicle registration to begin.")
        return

    if st.button("🔍 Check Eligibility", use_container_width=True):
        valid, cleaned_reg = validate_emergency_registration(reg)
        if not valid:
            st.error(cleaned_reg)
            return

        vehicle = db.check_emergency_vehicle(cleaned_reg)

        if not vehicle:
            st.error(
                "This vehicle registration is not in our emergency registry. "
                "Please contact your district authority to register."
            )
            return

        if not vehicle["is_enabled"]:
            st.warning(
                "Emergency service is currently unavailable "
                "for this vehicle category."
            )
            return

        st.session_state["emr_verified"] = dict(vehicle)
        st.rerun()

    verified = st.session_state.get("emr_verified")
    if not verified:
        return

    cat_label = EMERGENCY_CATEGORY_LABELS.get(
        verified["vehicle_category"],
        verified["vehicle_category"].title()
    )

    st.markdown(
        f'<div style="background:#FF3D0015;border:2px solid #FF3D00;'
        f'border-radius:12px;padding:16px;margin:8px 0">'
        f'<strong>✅ Vehicle Verified</strong><br>'
        f'Registration: <strong>{verified["registration_number"]}</strong><br>'
        f'Organisation: <strong>{verified["organisation"]}</strong><br>'
        f'Category: <strong>{cat_label}</strong><br>'
        f'Daily Limit Bypass: <strong>✅ Authorised</strong>'
        f'</div>',
        unsafe_allow_html=True
    )

    with st.form("emergency_form"):
        dl = st.text_input(
            "Driver's License Number",
            placeholder="DL-CTG-0042-2020"
        )

        col1, col2 = st.columns(2)
        with col1:
            city = st.selectbox("City", get_cities(), key="emr_city")
        with col2:
            area = st.selectbox(
                "Area",
                get_areas(city) if city else [],
                key="emr_area"
            )

        fuel = st.selectbox("Fuel Type Needed", FUEL_TYPES)

        stations     = []
        if city and area:
            stations = db.get_stations_by_area(city, area)

        station_data = []
        for s in stations:
            avail = db.get_available_fuel(s["id"], fuel)
            if avail > 0:
                station_data.append({
                    "id":        s["id"],
                    "name":      s["name"],
                    "address":   s["address"],
                    "available": avail,
                })

        if station_data:
            st.markdown("**Available Stations:**")
            for sd in station_data:
                st.markdown(
                    f'<div style="background:#132039;padding:8px 12px;'
                    f'border-radius:6px;margin:4px 0;color:#B0BEC5">'
                    f'<strong>{sd["name"]}</strong> — '
                    f'{fuel} available: <strong>'
                    f'{int(sd["available"])}L</strong>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            station_options = {sd["name"]: sd for sd in station_data}
            station_name    = st.selectbox(
                "Select Station", list(station_options.keys())
            )
        else:
            st.warning("No stations with available fuel in this area.")
            station_options = {}
            station_name    = None

        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input(
                "Fuel Amount Needed (litres)",
                min_value=1, max_value=500,
                value=100, step=1
            )
        with col2:
            eta_min = st.selectbox(
                "Estimated Arrival (minutes)", ETA_OPTIONS
            )

        submitted = st.form_submit_button(
            "🚨 Request Emergency Service",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            if not dl:
                st.error("Please enter your driver's license number.")
                st.stop()
            valid, cleaned_dl = validate_driver_license(dl)
            if not valid:
                st.error(cleaned_dl)
                st.stop()

            if not station_name or station_name not in station_options:
                st.error("Please select a station.")
                st.stop()

            sel_stn  = station_options[station_name]
            price    = db.get_fuel_price(fuel)
            avail    = db.get_available_fuel(sel_stn["id"], fuel)

            if amount > avail:
                st.error(
                    f"Requested amount exceeds available stock. "
                    f"Available: {int(avail)}L. "
                    f"Please request less or choose another station."
                )
                st.stop()

            valid, eta = validate_eta_minutes(eta_min)
            if not valid:
                st.error(eta)
                st.stop()

            eta_dt = get_eta_datetime(eta)
            token  = generate_emergency_token(db)
            est    = calculate_cost(amount, price)

            db.create_emergency_booking(
                token,
                verified["registration_number"],
                verified["vehicle_category"],
                verified["organisation"],
                sel_stn["id"],
                cleaned_dl,
                fuel, amount, price,
                eta, eta_dt
            )

            db.log_audit(
                1,
                "Emergency service booked",
                f"{verified['registration_number']} — "
                f"{fuel} {int(amount)}L at {sel_stn['name']}",
                "fuel"
            )

            try:
                eta_dt_obj = datetime.strptime(eta_dt, "%Y-%m-%d %H:%M:%S")
                eta_label  = eta_dt_obj.strftime("%I:%M %p")
            except Exception:
                eta_label  = eta_dt

            exp_label = f"Midnight, {date.today().strftime('%B %d, %Y')}"

            token_card(
                token, sel_stn["name"], sel_stn["address"],
                eta_dt, fuel, amount, est, exp_label,
                is_emergency=True
            )
            st.markdown(
                f'<div style="color:#B0BEC5;text-align:center;'
                f'margin-top:8px">ETA: approximately {eta_label}</div>',
                unsafe_allow_html=True
            )

            send_emergency_token(
                cleaned_dl + "@mock.com",
                cleaned_dl,
                token,
                verified["registration_number"],
                verified["organisation"],
                sel_stn["name"], sel_stn["address"],
                fuel, amount, eta_dt
            )

            st.session_state.pop("emr_verified", None)


def show_find_my_booking(db, logged_in: bool = False):
    st.markdown("## 🔍 Find My Booking")

    if logged_in:
        dl = st.session_state.driver_license
    else:
        dl_input = st.text_input(
            "Enter Driver's License Number",
            placeholder="DL-DHK-2341-2021"
        )
        if not dl_input:
            st.info("Enter your driver's license to find your booking.")
            return
        valid, dl = validate_driver_license(dl_input)
        if not valid:
            st.error(dl)
            return

    _raw    = db.get_booking_by_dl(dl)
    booking = dict(_raw) if _raw else None

    if booking:
        st.markdown("### Active Booking")
        token_display = (
            booking["token"] if logged_in
            else mask_token(booking["token"])
        )

        try:
            slot_dt  = datetime.strptime(
                booking["slot_datetime"], "%Y-%m-%d %H:%M:%S"
            )
            slot_str = slot_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        except Exception:
            slot_str = booking["slot_datetime"]

        late = is_slot_late(booking["slot_datetime"])

        late_badge = (
            "&nbsp;&nbsp;"
            "<span style='color:#FFB300;font-size:0.85rem'>"
            "⏰ Late arrival (same-day token still valid)</span>"
            if late else ""
        )

        st.markdown(
            f'<div style="background:#132039;border:1px solid #1E90FF44;'
            f'border-radius:12px;padding:20px;line-height:2.2">'
            f'<strong>Token:</strong> '
            f'<span style="font-family:monospace;font-size:1.1rem;'
            f'color:#1E90FF">{token_display}</span>'
            f'{late_badge}<br>'
            f'<strong>Station:</strong> '
            f'{booking.get("station_name", "—")}<br>'
            f'<strong>Time:</strong>   {slot_str}<br>'
            f'<strong>Fuel:</strong>   {booking["fuel_type"]} | '
            f'{int(booking["requested_amount"])}L<br>'
            f'<strong>Est. Cost:</strong> '
            f'{format_currency(booking["estimated_cost"])}<br>'
            f'<strong>Status:</strong> '
            f'{status_badge(booking["status"])}'
            f'</div>',
            unsafe_allow_html=True
        )

        if not logged_in:
            st.caption("Login to see full token and manage your booking.")

        if logged_in:
            postpone_count = db.get_postpone_count_this_month(dl)
            st.caption(
                f"Postponements used this month: {postpone_count} of 3"
            )

            col1, col2 = st.columns(2)
            with col1:
                if booking["status"] == "scheduled":
                    if st.button("🔄 Postpone", use_container_width=True):
                        st.session_state["show_postpone"] = True
                        st.rerun()
            with col2:
                if booking["status"] in ("scheduled", "pending_approval"):
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state["show_cancel_confirm"] = True
                        st.rerun()

            if st.session_state.get("show_postpone"):
                _show_postpone_flow(db, booking, postpone_count)

            if st.session_state.get("show_cancel_confirm"):
                _show_cancel_confirm(db, booking)

    else:
        st.info("No active booking found for this driver's license.")

    if logged_in:
        waitlist = db.get_waitlist_for_user(st.session_state.user_id)
        if waitlist:
            st.markdown("### Active Waitlist")
            for w in waitlist:
                try:
                    exp_dt  = datetime.strptime(
                        w["expires_at"], "%Y-%m-%d %H:%M:%S"
                    )
                    exp_str = exp_dt.strftime("%B %d at %I:%M %p")
                except Exception:
                    exp_str = w["expires_at"]

                pos        = db.get_waitlist_position(w["id"])
                type_label = (
                    "📋 Advance Waitlist"
                    if w["waitlist_type"] == "advance"
                    else "🔄 Postponement Waitlist"
                )

                st.markdown(
                    f'<div style="background:#132039;border:1px solid '
                    f'#FFB30044;border-radius:12px;padding:16px;margin:8px 0">'
                    f'<strong>{type_label}</strong><br>'
                    f'Station: {w["station_name"]}<br>'
                    f'Fuel: {w["fuel_type"]} | '
                    f'{int(w["requested_amount"])}L<br>'
                    f'Position: ~#{pos} in queue<br>'
                    f'Expires: {exp_str}'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if st.button(f"Leave Waitlist #{w['id']}",
                             key=f"leave_wl_{w['id']}"):
                    db.cancel_waitlist(w["id"])
                    st.success("You have been removed from the waitlist.")
                    st.rerun()

        _check_waitlist_offer(db)

    if dl:
        emr_booking = db.get_emergency_booking_by_dl(dl)
        if emr_booking:
            st.markdown("### Active Emergency Booking")
            try:
                eta_dt  = datetime.strptime(
                    emr_booking["eta_datetime"], "%Y-%m-%d %H:%M:%S"
                )
                eta_str = eta_dt.strftime("%I:%M %p")
            except Exception:
                eta_str = emr_booking["eta_datetime"]

            st.markdown(
                f'<div style="background:#FF3D0010;border:2px solid #FF3D00;'
                f'border-radius:12px;padding:16px">'
                f'<strong>🚨 Emergency Token:</strong> '
                f'<span style="font-family:monospace;color:#FF3D00">'
                f'{emr_booking["token"]}</span><br>'
                f'Station: {emr_booking["station_name"]}<br>'
                f'Fuel: {emr_booking["fuel_type"]} | '
                f'{int(emr_booking["requested_amount"])}L<br>'
                f'ETA: {eta_str}'
                f'</div>',
                unsafe_allow_html=True
            )


def _show_postpone_flow(db, booking, postpone_count):
    st.markdown("---")
    st.markdown("#### Postpone Appointment")

    if postpone_count >= 3:
        st.error(
            "You have used all 3 postponements for this month. "
            "If you cannot attend, please cancel instead."
        )
        if st.button("Close"):
            st.session_state.pop("show_postpone", None)
            st.rerun()
        return

    stn = db.get_station_by_id(booking["station_id"])

    try:
        slot_dt = datetime.strptime(
            booking["slot_datetime"], "%Y-%m-%d %H:%M:%S"
        )
        if datetime.now() >= slot_dt - timedelta(hours=1):
            st.error(
                "Postponements must be made at least 1 hour "
                "before your appointment time."
            )
            if st.button("Close"):
                st.session_state.pop("show_postpone", None)
                st.rerun()
            return
    except Exception:
        pass

    all_slots = []
    for days_ahead in range(3):
        target = date.today() + timedelta(days=days_ahead)
        slots  = db.get_available_slots(
            booking["station_id"], target,
            booking["vehicle_type"]
        )
        all_slots.extend(slots)

    if not all_slots:
        st.warning(
            "No slots available at this station in the next 3 days. "
            "You will be added to the postponement waitlist."
        )
        if st.button("Join Postponement Waitlist", type="primary"):
            db.set_pending_postpone(booking["token"], True)
            wl_id = db.join_waitlist(
                st.session_state.user_id,
                booking["station_id"],
                booking["fuel_type"],
                booking["vehicle_type"],
                booking["license_plate"],
                booking["requested_amount"],
                "postponement",
                booking["id"],
                0
            )
            if wl_id:
                pos = db.get_waitlist_position(wl_id)
                stn_name = stn["name"] if stn else "your station"
                send_postponement_waitlisted(
                    booking["email"], booking["full_name"],
                    booking["token"],
                    stn_name,
                    booking["slot_datetime"]
                )
                st.success(
                    f"Added to postponement waitlist (position #{pos}). "
                    f"Your original booking is still active."
                )
                show_email_confirmation(booking["email"])
            else:
                st.warning("Already on waitlist for this station.")
            st.session_state.pop("show_postpone", None)
            st.rerun()
    else:
        st.markdown("Select a new slot:")
        for days_ahead in range(3):
            target = date.today() + timedelta(days=days_ahead)
            label  = (
                "Today" if days_ahead == 0
                else "Tomorrow" if days_ahead == 1
                else target.strftime("%A, %B %d")
            )
            day_slots = db.get_available_slots(
                booking["station_id"], target,
                booking["vehicle_type"]
            )
            if day_slots:
                st.markdown(f"**{label}**")
                cols = st.columns(3)
                for idx, slot in enumerate(day_slots):
                    with cols[idx % 3]:
                        slot_str = slot.strftime("%Y-%m-%d %H:%M:%S")
                        time_str = slot.strftime("%I:%M %p")
                        btn_key  = f"postpone_slot_{slot_str}"
                        if st.button(time_str, key=btn_key,
                                     use_container_width=True):
                            old_slot  = booking["slot_datetime"]
                            db.postpone_booking(booking["token"], slot_str)
                            new_count = postpone_count + 1
                            stn_name  = stn["name"] if stn else "your station"
                            send_postponement_confirmed(
                                booking["email"], booking["full_name"],
                                booking["token"],
                                stn_name,
                                old_slot, slot_str,
                                booking["fuel_type"],
                                booking["requested_amount"],
                                new_count
                            )
                            show_email_confirmation(booking["email"])
                            st.success(
                                f"Appointment rescheduled to {time_str}. "
                                f"Token {booking['token']} unchanged. "
                                f"Postponements used: {new_count}/3"
                            )
                            st.session_state.pop("show_postpone", None)
                            st.rerun()

    if st.button("← Cancel Postponement"):
        st.session_state.pop("show_postpone", None)
        st.rerun()


def _show_cancel_confirm(db, booking):
    st.markdown("---")
    st.markdown("#### Cancel Booking")

    check = check_late_cancellation(
        db,
        booking["driver_license"],
        booking["slot_datetime"]
    )

    if check["tier"] != "clean":
        st.markdown(
            f'<div style="background:#FF3D0015;border:1px solid #FF3D00;'
            f'padding:12px;border-radius:8px">'
            f'{check["message"]}'
            f'</div>',
            unsafe_allow_html=True
        )

    col_confirm, col_keep = st.columns(2)
    with col_confirm:
        if st.button("✅ Confirm Cancellation",
                     use_container_width=True, type="primary"):
            db.cancel_booking(booking["token"])

            if check["hours"] > 0:
                apply_cancellation_ban(
                    db,
                    booking["driver_license"],
                    check["hours"]
                )

            penalty_msg = ""
            if check["hours"] > 0:
                susp = db.get_active_suspension(booking["driver_license"])
                if susp:
                    penalty_msg = format_suspension_message(dict(susp))

            station_name = booking.get("station_name", "your station")
            send_booking_cancelled_by_user(
                booking["email"],
                booking["full_name"],
                booking["token"],
                station_name,
                booking["slot_datetime"],
                penalty_msg
            )
            show_email_confirmation(booking["email"])

            st.success("Your booking has been cancelled.")
            if penalty_msg:
                st.warning(penalty_msg)
            st.session_state.pop("show_cancel_confirm", None)
            st.rerun()

    with col_keep:
        if st.button("Keep My Appointment", use_container_width=True):
            st.session_state.pop("show_cancel_confirm", None)
            st.rerun()


def _check_waitlist_offer(db):
    uid        = st.session_state.user_id
    _raw_offer = db.get_active_waitlist_offer(uid)
    offer      = dict(_raw_offer) if _raw_offer else None

    if not offer:
        return

    try:
        exp_dt  = datetime.strptime(
            offer["offer_expires_at"], "%Y-%m-%d %H:%M:%S"
        )
        mins    = max(0, int((exp_dt - datetime.now()).total_seconds() / 60))
        exp_str = exp_dt.strftime("%I:%M %p")
    except Exception:
        mins    = 0
        exp_str = offer["offer_expires_at"]

    price = db.get_fuel_price(offer["fuel_type"])
    est   = calculate_cost(offer["requested_amount"], price)

    token_disp = ""
    if offer.get("original_booking_id"):
        c = db.conn.cursor()
        c.execute("SELECT token FROM bookings WHERE id=?",
                  (offer["original_booking_id"],))
        row = c.fetchone()
        if row:
            token_disp = f"Token: {row['token']}"

    st.markdown(
        f'<div style="background:#FFD70015;border:2px solid #FFD700;'
        f'border-radius:12px;padding:16px;margin:12px 0">'
        f'<strong>🔔 SLOT AVAILABLE — ACTION REQUIRED</strong><br><br>'
        f'A slot has opened at {offer["station_name"]}.<br>'
        f'Fuel: <strong>{offer["fuel_type"]}</strong> | '
        f'<strong>{int(offer["requested_amount"])}L</strong><br>'
        f'Est. Cost: <strong>{format_currency(est)}</strong><br>'
        f'⏱️ Offer expires at: <strong>{exp_str}</strong> '
        f'({mins} minutes remaining)<br>'
        f'{token_disp}'
        f'</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Accept This Slot",
                     use_container_width=True, type="primary"):
            token    = generate_token(db)
            slot_dt  = datetime.now() + timedelta(minutes=5)
            slot_str = slot_dt.strftime("%Y-%m-%d %H:%M:%S")

            db.create_booking(
                token,
                uid, offer["station_id"],
                "advance",
                offer["vehicle_type"],
                offer["fuel_type"],
                offer["license_plate"],
                st.session_state.driver_license,
                st.session_state.user_name,
                st.session_state.email,
                offer["requested_amount"],
                price, slot_str
            )

            c = db.conn.cursor()
            c.execute(
                "UPDATE waitlist SET status='accepted' WHERE id=?",
                (offer["id"],)
            )
            db.conn.commit()

            db.remove_soft_reserve(
                offer["station_id"],
                offer["fuel_type"],
                offer["requested_amount"]
            )

            send_waitlist_offer_accepted(
                st.session_state.email,
                st.session_state.user_name,
                token, offer["station_name"],
                offer["station_address"],
                slot_str, offer["fuel_type"],
                offer["requested_amount"], est
            )
            show_email_confirmation(st.session_state.email)
            st.success(f"Slot confirmed! Your token is: {token}")
            st.rerun()

    with col2:
        if st.button("❌ Decline", use_container_width=True):
            c = db.conn.cursor()
            c.execute(
                "UPDATE waitlist SET status='declined' WHERE id=?",
                (offer["id"],)
            )
            db.conn.commit()

            db.remove_soft_reserve(
                offer["station_id"],
                offer["fuel_type"],
                offer["requested_amount"]
            )
            send_waitlist_offer_declined(
                st.session_state.email,
                st.session_state.user_name,
                offer["station_name"]
            )
            st.info("Offer declined.")
            st.rerun()


@require_role("station_admin")
def show_station_dashboard(db, station_id: int):
    stn = db.get_station_by_id(station_id)
    if not stn:
        st.error("Station not found. Please contact support.")
        return

    health         = db.get_station_health(station_id)
    today_bookings = db.get_todays_bookings_for_station(station_id)

    first_appt = min(
        (b["slot_datetime"] for b in today_bookings if b["slot_datetime"]),
        default=None
    )
    last_appt  = max(
        (b["slot_datetime"] for b in today_bookings if b["slot_datetime"]),
        default=None
    )

    st.markdown(
        f'<div style="background:#132039;border-radius:16px;'
        f'padding:24px;margin-bottom:16px">'
        f'<div style="font-size:1.2rem;font-weight:bold">'
        f'Good day, {stn["name"]} 👋</div>'
        f'<div style="color:#B0BEC5">'
        f'{datetime.now().strftime("%A, %B %d, %Y")}</div>'
        f'<hr style="border-color:#ffffff15;margin:12px 0">'
        f'📅 Bookings today: <strong>{len(today_bookings)}</strong><br>'
        f'⛽ First appointment: <strong>'
        f'{format_time_only(first_appt) if first_appt else "None"}'
        f'</strong><br>'
        f'🔚 Last appointment: <strong>'
        f'{format_time_only(last_appt) if last_appt else "None"}'
        f'</strong><br>',
        unsafe_allow_html=True
    )

    for fuel in ["octane", "diesel", "petrol", "kerosene"]:
        try:
            stk  = stn[f"{fuel}_stock"]
            cap  = stn[f"{fuel}_capacity"]
            pct  = get_fuel_pct(stk, cap)
            icon = "✅" if pct > 30 else "⚠️" if pct > 15 else "🚨"
            st.markdown(
                f'🛢️ {fuel.title()}: <strong>{int(stk)}L</strong> {icon}',
                unsafe_allow_html=True
            )
        except Exception:
            pass

    st.markdown("</div>", unsafe_allow_html=True)

    sub_tabs = st.tabs(["📋 Appointments", "🚶 Requests"])

    with sub_tabs[0]:
        bookings = db.get_todays_bookings_for_station(station_id)
        emr      = db.get_todays_emergency_for_station(station_id)

        all_rows = []

        for b in bookings:
            late   = is_slot_late(b["slot_datetime"])
            row_bg = "#FFB30015" if late else "#132039"
            status = "⏰ Late" if late else "📅 Scheduled"

            all_rows.append({
                "token":   b["token"],
                "vehicle": b["vehicle_type"],
                "fuel":    b["fuel_type"],
                "dl":      b["driver_license"],
                "time":    format_time_only(b["slot_datetime"]),
                "type":    get_booking_type_label(b["booking_type"]),
                "status":  status,
                "bg":      row_bg,
                "is_emr":  False,
            })

        for e in emr:
            if e["status"] == "scheduled":
                try:
                    eta_dt  = datetime.strptime(
                        e["eta_datetime"], "%Y-%m-%d %H:%M:%S"
                    )
                    eta_str = f"ETA {eta_dt.strftime('%I:%M %p')}"
                except Exception:
                    eta_str = "ETA —"

                all_rows.append({
                    "token":   e["token"],
                    "vehicle": e["vehicle_category"].title(),
                    "fuel":    e["fuel_type"],
                    "dl":      e["driver_license"],
                    "time":    eta_str,
                    "type":    "🚨 Emergency",
                    "status":  "📅 Expected",
                    "bg":      "#FF3D0015",
                    "is_emr":  True,
                })

        if not all_rows:
            st.info("No appointments remaining for today.")
        else:
            for row in all_rows:
                emr_badge = (
                    '&nbsp;<span style="background:#FF3D0033;'
                    'color:#FF3D00;padding:2px 8px;border-radius:12px;'
                    'font-size:0.8rem">🚨 EMERGENCY</span>'
                    if row["is_emr"] else ""
                )
                st.markdown(
                    f'<div style="background:{row["bg"]};padding:10px 14px;'
                    f'border-radius:8px;margin:4px 0">'
                    f'<code style="color:#1E90FF;font-size:1rem">'
                    f'{row["token"]}</code>{emr_badge}'
                    f'&nbsp;&nbsp;'
                    f'<span style="color:#FFFFFF">{row["vehicle"]}</span>'
                    f'&nbsp;&nbsp;'
                    f'<span style="color:#B0BEC5">{row["fuel"]}</span>'
                    f'&nbsp;&nbsp;'
                    f'<span style="color:#B0BEC5;font-size:0.85rem">'
                    f'{row["dl"]}</span>'
                    f'&nbsp;&nbsp;'
                    f'<span style="color:#FFD700;float:right">'
                    f'{row["time"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    with sub_tabs[1]:
        pending = db.get_pending_walkins(station_id)
        if not pending:
            st.info("No pending walk-in requests.")
        else:
            for req in pending:
                try:
                    sub_dt  = datetime.strptime(
                        req["created_at"], "%Y-%m-%d %H:%M:%S"
                    )
                    sub_str = sub_dt.strftime("%I:%M %p")
                except Exception:
                    sub_str = "—"

                st.markdown(
                    f'<div style="background:#132039;border:1px solid '
                    f'#1E90FF22;padding:12px;border-radius:8px;margin:6px 0">'
                    f'<strong>{req["vehicle_type"]}</strong> · '
                    f'{req["fuel_type"]} · '
                    f'{int(req["requested_amount"])}L<br>'
                    f'<span style="color:#B0BEC5;font-size:0.85rem">'
                    f'DL: {req["driver_license"]} | '
                    f'Requested: {sub_str}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Approve",
                                 key=f"approve_{req['id']}",
                                 use_container_width=True,
                                 type="primary"):
                        current_price = db.get_fuel_price(req["fuel_type"])
                        available     = db.get_available_fuel(
                            station_id, req["fuel_type"]
                        )
                        if req["requested_amount"] > available:
                            st.warning(
                                f"Insufficient fuel. Available: "
                                f"{int(available)}L. "
                                f"Request needs {int(req['requested_amount'])}L."
                            )
                        else:
                            db.approve_walkin(req["id"], current_price)
                            db.log_audit(
                                st.session_state.user_id,
                                "Walk-in approved",
                                f"{req['vehicle_type']} {req['fuel_type']}",
                                "fuel"
                            )
                            now_str = datetime.now().strftime(
                                "%I:%M %p, %B %d, %Y"
                            )
                            est = calculate_cost(
                                req["requested_amount"], current_price
                            )
                            send_walkin_approved(
                                req["email"], req["full_name"],
                                req["token"], stn["name"],
                                now_str, req["fuel_type"],
                                req["requested_amount"],
                                current_price, est,
                                req["vehicle_type"],
                                req["license_plate"]
                            )
                            st.success("Walk-in approved.")
                            st.rerun()
                with col2:
                    if st.button("❌ Deny",
                                 key=f"deny_{req['id']}",
                                 use_container_width=True):
                        reason = st.selectbox(
                            "Denial reason",
                            WALKIN_DENIAL_REASONS,
                            key=f"deny_reason_{req['id']}"
                        )
                        if st.button("Confirm Denial",
                                     key=f"confirm_deny_{req['id']}"):
                            db.deny_walkin(req["id"], reason)
                            db.log_audit(
                                st.session_state.user_id,
                                "Walk-in denied",
                                f"{req['vehicle_type']} — {reason}",
                                "fuel"
                            )
                            send_walkin_denied(
                                req["email"], req["full_name"],
                                stn["name"], reason
                            )
                            st.info("Request denied.")
                            st.rerun()


@require_role("station_admin")
def show_verify_token(db, station_id: int):
    st.markdown("## 🔍 Verify Token")

    token_input = st.text_input(
        "Enter Token",
        placeholder="A3F9KX2B or EX-B7K2MN9P",
        max_chars=15
    ).strip().upper()

    if st.button("🔍 Verify", use_container_width=True) and token_input:

        is_emergency = token_input.startswith("EX-")

        if is_emergency:
            _raw = db.get_emergency_by_token(token_input)
        else:
            _raw = db.get_booking_by_token(token_input)

        booking = dict(_raw) if _raw else None

        if not booking:
            st.error("Token not found. Please check and try again.")
            return

        if not is_emergency:
            if booking["station_id"] != station_id:
                st.error("This token is not valid for your station.")
                return
            if booking["status"] == "serviced":
                st.warning("This booking has already been serviced.")
                return
            if booking["status"] in ("cancelled", "denied", "no_show"):
                st.warning(
                    f"This token has status: "
                    f"{STATUS_LABELS.get(booking['status'], booking['status'])}"
                )
                return

        if is_emergency:
            st.markdown(
                '<div style="background:#FF3D0015;border:2px solid #FF3D00;'
                'border-radius:12px;padding:16px;margin:8px 0">'
                '<strong>🚨 EMERGENCY SERVICE</strong></div>',
                unsafe_allow_html=True
            )
            details = {
                "Registration": booking["registration_number"],
                "Organisation": booking["organisation"],
                "Category":     booking["vehicle_category"].title(),
                "Fuel":         booking["fuel_type"],
                "Requested":    f'{int(booking["requested_amount"])}L',
                "ETA":          format_time_only(booking["eta_datetime"]),
                "Status":       booking["status"].title(),
            }
        else:
            late    = is_slot_late(booking["slot_datetime"])
            details = {
                "Name":      booking["full_name"],
                "DL":        booking["driver_license"],
                "Vehicle":   booking["vehicle_type"],
                "Fuel":      booking["fuel_type"],
                "Requested": f'{int(booking["requested_amount"])}L',
                "Time":      format_time_only(booking["slot_datetime"]),
                "Status":    (
                    "⏰ Late (same day — token still valid)" if late
                    else STATUS_LABELS.get(
                        booking["status"], booking["status"]
                    )
                ),
                "Plate":     booking["license_plate"],
            }

        st.markdown(
            '<div style="background:#132039;border:1px solid #1E90FF44;'
            'border-radius:12px;padding:16px;line-height:2">',
            unsafe_allow_html=True
        )
        for k, v in details.items():
            st.markdown(f'<strong>{k}:</strong> {v}<br>',
                        unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if (
            booking["status"] in ("scheduled", "approved", "pending_approval")
            or (is_emergency and booking["status"] == "scheduled")
        ):
            st.markdown("---")
            with st.form("service_form"):
                max_val = float(booking["requested_amount"])
                actual  = st.number_input(
                    "Actual litres dispensed",
                    min_value=0.1,
                    max_value=max_val,
                    value=max_val,
                    step=0.1,
                    format="%.1f"
                )
                service_btn = st.form_submit_button(
                    "✅ Mark as Serviced",
                    use_container_width=True,
                    type="primary"
                )

                if service_btn:
                    valid, validated_actual = validate_dispensed_amount(
                        actual, booking["requested_amount"]
                    )
                    if not valid:
                        st.error(validated_actual)
                        st.stop()

                    stn_obj = db.get_station_by_id(station_id)

                    if is_emergency:
                        result = db.service_emergency(
                            token_input, validated_actual
                        )
                        db.log_audit(
                            st.session_state.user_id,
                            "Emergency service completed",
                            f"Token {token_input} — "
                            f"{validated_actual}L {booking['fuel_type']}",
                            "fuel"
                        )
                    else:
                        result = db.mark_serviced(
                            token_input, validated_actual
                        )
                        db.log_audit(
                            st.session_state.user_id,
                            "Marked as Serviced",
                            f"Token {token_input} — "
                            f"{validated_actual}L {booking['fuel_type']}",
                            "fuel"
                        )

                    if result:
                        now_str = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        stn_name = stn_obj["name"] if stn_obj else "Station"
                        receipt  = (
                            generate_emergency_receipt_text(
                                booking, stn_name,
                                validated_actual, now_str
                            )
                            if is_emergency
                            else generate_receipt_text(
                                booking, stn_name,
                                validated_actual, now_str
                            )
                        )
                        st.success("✅ Booking marked as serviced.")
                        st.code(receipt, language=None)
                        send_service_receipt(
                            booking.get(
                                "email",
                                booking.get("driver_license", "") + "@mock.com"
                            ),
                            booking.get(
                                "full_name",
                                booking.get("organisation", "")
                            ),
                            receipt
                        )
                        st.rerun()


@require_role("station_admin")
def show_station_analytics(db, station_id: int):
    st.markdown("## 📊 Station Analytics")
    period = period_selector("stn_analytics")
    data   = db.get_station_analytics(station_id, period)
    health = db.get_station_health(station_id)

    st.markdown(
        f'Station Status: {health_badge(health)}',
        unsafe_allow_html=True
    )
    st.markdown("")

    if not data["daily"]:
        st.info("No service data available for this period yet.")
        return

    total_serviced  = sum(r["total"]     for r in data["daily"])
    total_dispensed = sum(
        r["dispensed"] for r in data["daily"] if r["dispensed"]
    )
    total_revenue   = sum(
        r["revenue"] for r in data["daily"] if r["revenue"]
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Vehicles Serviced", total_serviced)
    col2.metric("Fuel Dispensed",    f"{int(total_dispensed)}L")
    col3.metric("Est. Revenue",      format_currency_int(total_revenue))

    df_daily = pd.DataFrame([dict(r) for r in data["daily"]])
    if not df_daily.empty:
        fig = px.bar(
            df_daily, x="day", y="total",
            title="Vehicles Serviced Per Day",
            color_discrete_sequence=["#1E90FF"],
            labels={"day": "Date", "total": "Vehicles"}
        )
        fig.update_layout(
            plot_bgcolor="#0A1628",
            paper_bgcolor="#0A1628",
            font_color="#FFFFFF"
        )
        st.plotly_chart(fig, use_container_width=True)

    if data["by_vehicle"]:
        df_veh = pd.DataFrame([dict(r) for r in data["by_vehicle"]])
        fig2   = px.bar(
            df_veh, x="vehicle_type", y="cnt",
            title="Breakdown by Vehicle Type",
            color="vehicle_type",
            labels={"vehicle_type": "Vehicle", "cnt": "Count"}
        )
        fig2.update_layout(
            plot_bgcolor="#0A1628",
            paper_bgcolor="#0A1628",
            font_color="#FFFFFF",
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)


@require_role("station_admin")
def show_pump_management(db, station_id: int):
    st.markdown("## 🔧 Pump Management")
    stn        = db.get_station_by_id(station_id)
    if not stn:
        st.error("Station not found.")
        return
    pump_count = stn["pump_count"]

    st.markdown(f"**Station:** {stn['name']}  |  **Pumps:** {pump_count}")
    st.markdown("---")

    st.markdown("### 🚨 Emergency Close Entire Station")
    st.warning(
        "This will cancel ALL remaining bookings for today "
        "and notify all affected customers."
    )
    if st.button("⚠️ Emergency Close Station", use_container_width=True):
        st.session_state["confirm_station_close"] = True

    if st.session_state.get("confirm_station_close"):
        st.error("Are you sure? This cannot be undone for today.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm Emergency Close",
                         type="primary", use_container_width=True):
                today_bookings = db.get_todays_bookings_for_station(
                    station_id
                )
                cancelled = 0
                for b in today_bookings:
                    if b["status"] == "scheduled":
                        db.cancel_booking(b["token"])
                        area   = stn["area"]
                        nearby = get_adjacent_areas(area)
                        send_booking_cancelled_by_system(
                            b["email"], b["full_name"],
                            b["token"], stn["name"],
                            b["slot_datetime"], nearby
                        )
                        cancelled += 1

                db.log_audit(
                    st.session_state.user_id,
                    "Emergency station closure",
                    f"{cancelled} bookings cancelled",
                    "fuel"
                )
                st.success(
                    f"Station closed. {cancelled} bookings cancelled "
                    f"and customers notified."
                )
                st.session_state.pop("confirm_station_close", None)
                st.rerun()
        with col2:
            if st.button("← Cancel", use_container_width=True):
                st.session_state.pop("confirm_station_close", None)
                st.rerun()

    st.markdown("---")
    st.markdown("### 🔧 Individual Pump Maintenance")
    st.info(
        "Mark a pump as under maintenance to block new bookings. "
        "Existing bookings are not affected."
    )
    for pump_num in range(1, pump_count + 1):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Pump {pump_num}**")
        with col2:
            if st.button(f"Mark Maintenance", key=f"maint_{pump_num}"):
                db.log_audit(
                    st.session_state.user_id,
                    "Pump marked for maintenance",
                    f"Pump {pump_num} — maintenance flagged",
                    "fuel"
                )
                st.info(f"Pump {pump_num} flagged for maintenance.")


@require_role("station_admin")
def show_inventory_management(db, station_id: int):
    st.markdown("## 📦 Inventory Management")
    stn    = db.get_station_by_id(station_id)
    if not stn:
        st.error("Station not found.")
        return
    health = db.get_station_health(station_id)

    col_h, col_wi = st.columns([3, 1])
    with col_h:
        st.markdown(
            f'Station Status: {health_badge(health)}',
            unsafe_allow_html=True
        )
    with col_wi:
        walkin_on = bool(stn["walkin_enabled"])
        new_state = st.toggle("Walk-ins", value=walkin_on,
                               key="walkin_toggle")
        if new_state != walkin_on:
            db.toggle_walkin(station_id, new_state)
            db.log_audit(
                st.session_state.user_id,
                "Walk-in toggle",
                f"Walk-ins {'enabled' if new_state else 'disabled'}",
                "fuel"
            )
            st.rerun()

    st.markdown("---")
    st.markdown("### Current Fuel Levels")

    for fuel in ["Octane", "Diesel", "Petrol", "Kerosene"]:
        fuel_lower = fuel.lower()
        try:
            stock = stn[f"{fuel_lower}_stock"]
            cap   = stn[f"{fuel_lower}_capacity"]
        except Exception:
            continue
        avail = db.get_available_fuel(station_id, fuel)
        fuel_gauge_bar(fuel, stock, cap, fuel)
        st.caption(f"Available for booking: {int(avail)}L")

    st.markdown("---")
    st.markdown("### Log Resupply")

    with st.form("resupply_form"):
        col1, col2 = st.columns(2)
        with col1:
            rs_fuel = st.selectbox("Fuel Type", FUEL_TYPES, key="rs_fuel")
        with col2:
            fuel_lower = rs_fuel.lower()
            try:
                curr_stock = stn[f"{fuel_lower}_stock"]
                capacity   = stn[f"{fuel_lower}_capacity"]
                remaining  = capacity - curr_stock
            except Exception:
                remaining  = 5000

            rs_qty = st.number_input(
                f"Quantity (max {int(remaining)}L)",
                min_value=1,
                max_value=int(max(remaining, 1)),
                value=min(1000, int(max(remaining, 1))),
                step=100
            )

        rs_submitted = st.form_submit_button(
            "Log Resupply", use_container_width=True, type="primary"
        )

        if rs_submitted:
            valid, qty = validate_resupply_amount(rs_qty, remaining)
            if not valid:
                st.error(qty)
            else:
                db.log_resupply(
                    station_id, rs_fuel, qty,
                    st.session_state.user_id
                )
                db.log_audit(
                    st.session_state.user_id,
                    "Logged resupply",
                    f"+{qty}L {rs_fuel}",
                    "fuel"
                )
                st.success(f"✅ Resupply logged: +{qty}L {rs_fuel}")
                st.rerun()

    st.markdown("### Resupply History")
    history = db.get_resupply_history(station_id)
    if history:
        rows = [
            {
                "Date":  format_date_only(h["logged_at"]),
                "Fuel":  h["fuel_type"],
                "Added": f'+{int(h["quantity_added"])}L',
            }
            for h in history
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.caption("No resupply history.")


@require_role("government_official")
def show_govt_control_panel(db, section: str = "fuel"):
    if section == "fuel":
        _show_govt_fuel(db)
    elif section == "electricity":
        _show_govt_electricity(db)


def _show_govt_fuel(db):
    st.markdown("## ⛽ Fuel Management")

    all_stations = db.get_all_stations()
    critical     = []
    for s in all_stations:
        for fuel in ["octane", "diesel", "petrol", "kerosene"]:
            try:
                cap = s[f"{fuel}_capacity"]
                stk = s[f"{fuel}_stock"]
                if cap and cap > 0 and (stk / cap) < 0.20:
                    critical.append(
                        f"{s['name']}: {fuel.title()} at "
                        f"{get_fuel_pct(stk, cap):.1f}%"
                    )
            except Exception:
                pass

    if critical:
        alerts = "<br>".join(critical)
        st.markdown(
            f'<div style="background:#FF3D0015;border:2px solid #FF3D00;'
            f'border-radius:12px;padding:16px;margin-bottom:12px">'
            f'🚨 <strong>CRITICAL ALERTS</strong><br>{alerts}</div>',
            unsafe_allow_html=True
        )

    analytics_tab, trajectory_tab, compare_tab = st.tabs([
        "📊 Analytics", "📈 Trajectory", "🔁 Compare"
    ])
    limits_tab, prices_tab, vehicles_tab = st.tabs([
        "⚖️ Daily Limits", "💰 Prices", "🚨 Special Vehicles"
    ])
    announce_tab, reset_tab, search_tab, audit_tab = st.tabs([
        "📢 Announcements", "🔑 Password Reset",
        "🔍 Search", "📋 Audit Log"
    ])

    with analytics_tab:
        period = period_selector("govt_analytics")
        data   = db.get_national_analytics(period)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Stations", len(all_stations))
        c3.metric("Cities", 2)

        if data["daily"]:
            df = pd.DataFrame([dict(r) for r in data["daily"]])
            fig = px.line(
                df, x="day", y="total",
                title="National Bookings Trend",
                color_discrete_sequence=["#1E90FF"]
            )
            fig.update_layout(
                plot_bgcolor="#0A1628",
                paper_bgcolor="#0A1628",
                font_color="#FFFFFF"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Station Inventory Overview:**")
        rows = []
        for s in all_stations:
            h = db.get_station_health(s["id"])
            rows.append({
                "Station":  s["name"],
                "City":     s["city"],
                "Octane":   f'{int(s["octane_stock"])}L',
                "Diesel":   f'{int(s["diesel_stock"])}L',
                "Petrol":   f'{int(s["petrol_stock"])}L',
                "Kerosene": f'{int(s["kerosene_stock"])}L',
                "Status":   HEALTH_LABELS.get(h, h),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    with trajectory_tab:
        st.markdown("### Stock Trajectory")
        for s in all_stations:
            h = db.get_station_health(s["id"])

            c = db.conn.cursor()
            c.execute("""
                SELECT logged_at FROM resupply_log
                WHERE station_id=?
                ORDER BY logged_at DESC LIMIT 1
            """, (s["id"],))
            last_rs = c.fetchone()

            if last_rs:
                try:
                    rs_dt    = datetime.strptime(
                        last_rs[0], "%Y-%m-%d %H:%M:%S"
                    )
                    days_ago = (datetime.now() - rs_dt).days
                    rs_str   = f"{days_ago} days ago"
                    flag     = " 🚩" if days_ago > 7 else ""
                except Exception:
                    rs_str = "—"
                    flag   = ""
            else:
                rs_str = "No resupply recorded"
                flag   = " 🚩"

            with st.expander(
                f"{s['name']} ({s['city']}) — {HEALTH_LABELS.get(h, h)}"
            ):
                for fuel in ["Octane", "Diesel", "Petrol", "Kerosene"]:
                    fl = fuel.lower()
                    try:
                        stk = s[f"{fl}_stock"]
                        cap = s[f"{fl}_capacity"]
                        fuel_gauge_bar(fuel, stk, cap, fuel)
                    except Exception:
                        pass
                st.caption(f"Last resupply: {rs_str}{flag}")

    with compare_tab:
        st.markdown("### Station Comparison")
        stn_names = [s["name"] for s in all_stations]

        if len(stn_names) < 2:
            st.info("At least 2 stations needed for comparison.")
        else:
            sel = st.multiselect(
                "Select 2 or 3 stations to compare",
                stn_names, max_selections=3
            )
            if len(sel) >= 2:
                comp_rows = []
                for s in all_stations:
                    if s["name"] not in sel:
                        continue
                    h = db.get_station_health(s["id"])
                    comp_rows.append({
                        "Station":  s["name"],
                        "City":     s["city"],
                        "Status":   HEALTH_LABELS.get(h, h),
                        "Octane":   f'{get_fuel_pct(s["octane_stock"], s["octane_capacity"])}%',
                        "Diesel":   f'{get_fuel_pct(s["diesel_stock"], s["diesel_capacity"])}%',
                        "Petrol":   f'{get_fuel_pct(s["petrol_stock"], s["petrol_capacity"])}%',
                        "Kerosene": f'{get_fuel_pct(s["kerosene_stock"], s["kerosene_capacity"])}%',
                    })
                st.dataframe(
                    pd.DataFrame(comp_rows), use_container_width=True
                )

    with limits_tab:
        st.markdown("### Daily Limit Control")
        limits = db.get_all_daily_limits()
        if limits:
            df_lim = pd.DataFrame([dict(r) for r in limits])
            st.dataframe(
                df_lim[["vehicle_type", "fuel_type", "max_litres"]],
                use_container_width=True
            )

        st.markdown("**Update a Daily Limit:**")
        with st.form("limit_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                lim_veh  = st.selectbox("Vehicle", VEHICLE_TYPES,
                                         key="lim_veh")
            with col2:
                lim_fuel = st.selectbox("Fuel", FUEL_TYPES,
                                         key="lim_fuel")
            with col3:
                lim_val  = st.number_input(
                    "Max Litres", min_value=1,
                    max_value=300, value=40, step=1
                )
            if st.form_submit_button("Save Limit",
                                      use_container_width=True):
                if lim_val <= 0:
                    st.error("Limit must be greater than zero.")
                else:
                    old_limit = db.get_daily_limit(lim_veh, lim_fuel)
                    db.set_daily_limit(
                        lim_veh, lim_fuel, lim_val,
                        st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        "Updated daily limit",
                        f"{lim_veh} + {lim_fuel}: "
                        f"{old_limit}L → {lim_val}L",
                        "fuel"
                    )
                    st.success(
                        f"Limit updated: {lim_veh} + {lim_fuel} = {lim_val}L"
                    )
                    st.rerun()

    with prices_tab:
        st.markdown("### Fuel Price Management")
        prices = db.get_all_fuel_prices()
        for p in prices:
            st.markdown(
                f'<div style="background:#132039;padding:10px 14px;'
                f'border-radius:8px;margin:4px 0">'
                f'<strong>{p["fuel_type"]}</strong>: '
                f'{format_currency(p["price_per_litre"])}/L '
                f'<span style="color:#B0BEC5;font-size:0.85rem">'
                f'Updated: {format_date_only(p["updated_at"])}'
                f'</span></div>',
                unsafe_allow_html=True
            )

        st.markdown("**Update a Price:**")
        with st.form("price_form"):
            col1, col2 = st.columns(2)
            with col1:
                p_fuel = st.selectbox("Fuel Type", FUEL_TYPES, key="p_fuel")
            with col2:
                p_val  = st.number_input(
                    "New Price (৳/L)",
                    min_value=50.0, max_value=500.0,
                    value=125.0, step=0.5, format="%.2f"
                )
            if st.form_submit_button("Update Price",
                                      use_container_width=True):
                valid, new_price = validate_fuel_price(p_val)
                if not valid:
                    st.error(new_price)
                else:
                    old_price = db.get_fuel_price(p_fuel)
                    db.set_fuel_price(
                        p_fuel, new_price, st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        "Updated fuel price",
                        f"{p_fuel}: ৳{old_price} → ৳{new_price}",
                        "fuel"
                    )
                    st.success(
                        f"Price updated: {p_fuel} = "
                        f"{format_currency(new_price)}/L. "
                        f"Applies to new bookings only."
                    )
                    st.rerun()

    with vehicles_tab:
        st.markdown("### Emergency Vehicle Registry")

        st.markdown("**Category Eligibility:**")
        eligibility = db.get_eligibility_settings()
        for e in eligibility:
            col1, col2 = st.columns([3, 1])
            with col1:
                label = EMERGENCY_CATEGORY_LABELS.get(
                    e["vehicle_category"],
                    e["vehicle_category"].title()
                )
                st.markdown(label)
            with col2:
                new_state = st.toggle(
                    "Enabled",
                    value=bool(e["is_enabled"]),
                    key=f"elig_{e['vehicle_category']}"
                )
                if new_state != bool(e["is_enabled"]):
                    db.set_eligibility(
                        e["vehicle_category"], new_state,
                        st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        f"{'Enabled' if new_state else 'Disabled'} category",
                        f"{e['vehicle_category'].title()} emergency bypass",
                        "fuel"
                    )
                    st.rerun()

        st.markdown("---")
        st.markdown("**Registered Vehicles:**")
        vehicles = db.get_all_special_vehicles()
        if vehicles:
            rows = [
                {
                    "Registration": v["registration_number"],
                    "Category":     v["vehicle_category"].title(),
                    "Organisation": v["organisation"],
                    "Status":       "✅ Active" if v["is_active"] else "❌ Inactive",
                    "Eligible":     "✅ Yes"    if v["is_enabled"] else "❌ No",
                }
                for v in vehicles
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.markdown("**Register New Vehicle:**")
        with st.form("reg_vehicle_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_reg = st.text_input("Registration Number",
                                         placeholder="AMB-CTG-042")
                new_cat = st.selectbox(
                    "Category",
                    ["ambulance", "fire", "police",
                     "government", "military"]
                )
            with col2:
                new_org = st.text_input(
                    "Organisation",
                    placeholder="Dhaka Medical College"
                )
            if st.form_submit_button("Register Vehicle",
                                      use_container_width=True):
                valid, cleaned = validate_emergency_registration(new_reg)
                if not valid:
                    st.error(cleaned)
                elif not new_org or len(new_org.strip()) < 5:
                    st.error("Please enter a valid organisation name.")
                else:
                    db.register_special_vehicle(
                        cleaned, new_cat, new_org.strip(),
                        st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        "Registered emergency vehicle",
                        f"{cleaned} — {new_cat.title()} — {new_org}",
                        "fuel"
                    )
                    st.success(f"Vehicle {cleaned} registered.")
                    st.rerun()

    with announce_tab:
        st.markdown("### Announcements")
        all_ann = db.get_all_announcements()

        if all_ann:
            for ann in all_ann:
                try:
                    exp_dt  = datetime.strptime(
                        ann["expires_at"], "%Y-%m-%d %H:%M:%S"
                    )
                    is_live = (
                        bool(ann["is_active"]) and exp_dt > datetime.now()
                    )
                except Exception:
                    is_live = False

                with st.expander(
                    f"{ann['title']} — {'✅ Active' if is_live else '⏰ Expired'}"
                ):
                    st.markdown(ann["message"])
                    st.caption(
                        f"Expires: {format_datetime(ann['expires_at'])}"
                    )
                    if is_live:
                        if st.button("Deactivate",
                                     key=f"deact_{ann['id']}"):
                            db.deactivate_announcement(ann["id"])
                            st.rerun()

        st.markdown("---")
        st.markdown("**Publish New Announcement:**")
        with st.form("ann_form"):
            ann_title   = st.text_input("Title", max_chars=100)
            ann_message = st.text_area("Message", max_chars=500)
            ann_expires = st.date_input(
                "Expires On",
                value=get_default_expiry_date(),
                min_value=date.today()
            )
            if st.form_submit_button("📢 Publish",
                                      use_container_width=True,
                                      type="primary"):
                valid, msg = validate_announcement(
                    ann_title, ann_message, ann_expires
                )
                if not valid:
                    st.error(msg)
                else:
                    exp_dt = datetime.combine(
                        ann_expires, datetime.max.time()
                    )
                    db.publish_announcement(
                        ann_title.strip(),
                        ann_message.strip(),
                        exp_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        st.session_state.user_id
                    )
                    db.log_audit(
                        st.session_state.user_id,
                        "Published announcement",
                        ann_title.strip(),
                        "fuel"
                    )
                    st.success("Announcement published.")
                    st.rerun()

    with reset_tab:
        st.markdown("### Admin Password Reset")
        admins = db.get_all_admins()
        if not admins:
            st.info("No admin accounts found.")
        else:
            admin_options = {
                f"{a['full_name']} ({a['role'].replace('_',' ').title()})": a
                for a in admins
            }
            sel_admin = st.selectbox(
                "Select Admin", list(admin_options.keys())
            )
            if st.button("Generate Temporary Password",
                         use_container_width=True):
                admin = admin_options[sel_admin]
                temp  = generate_temp_password()
                db.reset_password(admin["id"], temp)
                db.log_audit(
                    st.session_state.user_id,
                    "Password reset",
                    f"Reset password for {admin['full_name']}",
                    "fuel"
                )
                st.success(
                    f"Temporary password generated for "
                    f"{admin['full_name']}:"
                )
                st.code(temp, language=None)
                st.caption(
                    "Share this with the admin. "
                    "They must change it on next login."
                )

    with search_tab:
        st.markdown("### Plate / License Search")
        search_type = st.radio(
            "Search by:",
            ["License Plate", "Driver's License"],
            horizontal=True
        )
        search_val = st.text_input(
            "Enter value",
            placeholder=(
                "DHAKA-METRO-GA-11-2233"
                if search_type == "License Plate"
                else "DL-DHK-2341-2021"
            )
        )

        if st.button("🔍 Search") and search_val:
            results = []
            if search_type == "License Plate":
                valid, cleaned = validate_license_plate(search_val)
                if not valid:
                    st.error(cleaned)
                else:
                    results = db.search_by_plate(cleaned)
            else:
                valid, cleaned = validate_driver_license(search_val)
                if not valid:
                    st.error(cleaned)
                else:
                    results = db.search_by_dl(cleaned)

                    susp = db.get_active_suspension(cleaned)
                    if susp:
                        susp_dict = dict(susp)
                        st.markdown(
                            f'<div style="background:#FF3D0015;'
                            f'border:1px solid #FF3D00;padding:12px;'
                            f'border-radius:8px;margin:8px 0">'
                            f'🚫 <strong>Active Suspension</strong><br>'
                            f'{format_suspension_message(susp_dict)}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                        if st.button("Lift Suspension", key="lift_susp"):
                            st.session_state["show_lift"] = susp_dict["id"]
                            st.rerun()

                    if st.session_state.get("show_lift"):
                        with st.form("lift_form"):
                            lift_note = st.text_area(
                                "Reason for lifting suspension"
                            )
                            if st.form_submit_button("Confirm Lift"):
                                if len(lift_note.strip()) < 10:
                                    st.error(
                                        "Please provide a meaningful "
                                        "reason (min 10 characters)."
                                    )
                                else:
                                    db.lift_suspension(
                                        st.session_state.show_lift,
                                        st.session_state.user_id,
                                        lift_note.strip()
                                    )
                                    db.log_audit(
                                        st.session_state.user_id,
                                        "Suspension lifted",
                                        f"DL: {cleaned} — "
                                        f"Reason: {lift_note.strip()}",
                                        "fuel"
                                    )
                                    send_suspension_lifted(
                                        cleaned + "@mock.com",
                                        cleaned
                                    )
                                    st.success("Suspension lifted.")
                                    st.session_state.pop("show_lift", None)
                                    st.rerun()

            if results:
                rows = [
                    {
                        "Token":   r["token"],
                        "Station": r["station_name"],
                        "Fuel":    r["fuel_type"],
                        "Amount":  f'{int(r["requested_amount"])}L',
                        "Status":  STATUS_LABELS.get(
                            r["status"], r["status"]
                        ),
                        "Date":    format_date_only(r["created_at"]),
                    }
                    for r in results
                ]
                st.dataframe(pd.DataFrame(rows),
                             use_container_width=True)
            else:
                st.info("No booking history found.")

    with audit_tab:
        st.markdown("### Fuel Audit Log")
        log = db.get_audit_log(log_type="fuel", limit=100)
        if log:
            rows = [
                {
                    "Time":    format_datetime(e["timestamp"]),
                    "User":    e["user_name"],
                    "Role":    e["role"].replace("_", " ").title(),
                    "Action":  e["action"],
                    "Details": e["details"] or "—",
                }
                for e in log
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No audit entries yet.")


def _show_govt_electricity(db):
    st.markdown("## ⚡ Electricity Management")

    analytics_tab, audit_tab = st.tabs([
        "📊 Outage Analytics", "📋 PDB Audit Log"
    ])

    with analytics_tab:
        st.markdown("### Load Shedding Analytics")

        col1, col2 = st.columns(2)
        with col1:
            city_filter = st.selectbox(
                "City", ["All Cities"] + get_cities(),
                key="elec_analytics_city"
            )
        with col2:
            period = st.selectbox(
                "Period",
                ["This Week", "This Month", "This Year"],
                key="elec_analytics_period"
            )

        period_map = {
            "This Week":  "week",
            "This Month": "month",
            "This Year":  "year",
        }
        period_val = period_map.get(period, "week")
        city_val   = None if city_filter == "All Cities" else city_filter

        data = db.get_electricity_analytics(city_val, period_val)

        if not data:
            st.info("No load shedding data for this period.")
        else:
            city_totals = {}
            for row in data:
                city = row["city"]
                hrs  = row["total_hours"] or 0
                city_totals[city] = city_totals.get(city, 0) + hrs

            cols = st.columns(len(city_totals))
            for i, (city, hrs) in enumerate(city_totals.items()):
                cols[i].metric(f"{city} — Total Outage Hours",
                               f"{hrs:.1f} hrs")

            df = pd.DataFrame([dict(r) for r in data])
            if not df.empty:
                fig = px.bar(
                    df, x="area", y="total_hours",
                    title="Outage Hours by Area",
                    color="city",
                    color_discrete_map={
                        "Dhaka":      "#1E90FF",
                        "Chattogram": "#00C853",
                    },
                    labels={
                        "area":        "Area",
                        "total_hours": "Hours",
                        "city":        "City",
                    }
                )
                fig.update_layout(
                    plot_bgcolor="#0A1628",
                    paper_bgcolor="#0A1628",
                    font_color="#FFFFFF"
                )
                st.plotly_chart(fig, use_container_width=True)

                sorted_data = sorted(
                    data,
                    key=lambda x: x["total_hours"] or 0,
                    reverse=True
                )
                if len(sorted_data) > 1:
                    st.success(
                        f"Least affected: **{sorted_data[-1]['area']}** "
                        f"— {sorted_data[-1]['total_hours']:.1f} hrs"
                    )
                    st.error(
                        f"Most affected: **{sorted_data[0]['area']}** "
                        f"— {sorted_data[0]['total_hours']:.1f} hrs"
                    )

    with audit_tab:
        st.markdown("### PDB Activity Log")
        log = db.get_audit_log(log_type="electricity", limit=100)
        if log:
            rows = [
                {
                    "Time":    format_datetime(e["timestamp"]),
                    "Admin":   e["user_name"],
                    "Action":  e["action"],
                    "Details": e["details"] or "—",
                }
                for e in log
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No PDB audit entries yet.")
