# চলার সঙ্গী (Cholar Shongi)

**Travel Companion** — A smart fuel booking and load shedding management system for Bangladesh.

Built with Python and Streamlit as a first-year university course project.

---

## Live Demo

[Click here to open the app]((https://cholar-shongi.streamlit.app/))

---

## What It Does

Bangladesh faces two major daily infrastructure challenges:

1. **Load Shedding** — Citizens have no easy way to check scheduled power cuts for their area ahead of time.
2. **Fuel Queues** — No appointment system exists at fuel stations, leading to long unmanaged queues.

Cholar Shongi solves both problems in one application.

---

## Features

### Electricity
- Public load shedding schedule viewer — no login required
- City and area filtering
- Active, upcoming and expired schedule categories
- 48-hour change notification banner
- 7-day forward visibility window

### Fuel
- Advance slot booking up to 3 days ahead
- Smart slot suggestion with full grid browse option
- Walk-in (on-demand) booking with station admin approval
- Emergency vehicle priority service (no login required)
- Find My Booking — retrieve token with driver's license
- Waitlist system when all slots are taken
- Postponement system (max 3 per month)
- Cancellation with late cancellation policy enforcement
- No-show tracking with escalating suspension system

### Government Control Panel
- National fuel analytics and stock trajectory
- Daily limit and fuel price management
- Emergency vehicle registry
- Public announcement publishing
- Admin password reset
- License plate and driver's license search
- Full fuel and electricity audit logs

---

## Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| Government Official | govt@bangladesh.gov.bd | govt2024 |
| PDB Admin (Dhaka) | pdb.dhaka@pdb.gov.bd | pdbdhaka24 |
| PDB Admin (Chattogram) | pdb.ctg@pdb.gov.bd | pdbctg2024 |
| Station Admin (Gulshan) | admin@gulshan1.fuel.bd | station2024 |
| Station Admin (Dhanmondi) | admin@dhanmondi1.fuel.bd | station2024 |
| Station Admin (Agrabad) | admin@agrabad1.fuel.bd | station2024 |
| Regular User | rahim.uddin@gmail.com | user2024 |
| Suspended User (no-show) | karim.miah@gmail.com | user2024 |
| Suspended User (late cancel) | nusrat.jahan@gmail.com | user2024 |

> These are demonstration credentials intentionally made public for academic review.


---

## Interesting Demo Scenarios

| Scenario | How to trigger |
|----------|----------------|
| Critical fuel alert | Government login → Fuel Management → Analytics. Dhanmondi shows Octane at 12% and Petrol at 10%. |
| Fully closed fuel type | Any user → Fuel → Advance Booking → Chattogram → GEC → GEC Filling Station. Petrol is 0L. |
| Active no-show suspension | Login as karim.miah@gmail.com. Suspended for 4 more days. |
| Active late-cancel suspension | Login as nusrat.jahan@gmail.com. Suspended for 12 more hours. |
| 48-hour change banner | Electricity → Dhaka → Gulshan. Gulshan Feeder A was edited 6 hours ago. |
| Emergency vehicle disabled | Emergency Services → enter POL-DHK-001. Police category is disabled. |
| Emergency vehicle enabled | Emergency Services → enter FIRE-CTG-001. Chattogram Fire Service. |
| Pending walk-in request | Login as Gulshan station admin → Dashboard → Requests tab. |
| Scheduled emergency arrival | Login as Gulshan station admin → Dashboard. EX-M3N4O5 arriving in approximately 20 minutes. |
| No resupply alert | Government login → Fuel Management → Trajectory. Dhanmondi has no resupply history. |
| Waitlist entries | Login as rahim.uddin@gmail.com → Find My Booking. Active waitlist at Dhanmondi. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Frontend | Streamlit 1.35.0 |
| Database | SQLite (single file, no server) |
| Password Security | bcrypt (rounds=12) |
| Charts | Plotly 5.20.0 |
| Data Display | Pandas 2.2.1 |
| Animations | streamlit-lottie 0.0.5 |
| Email | smtplib (Gmail SMTP for live demo) |

---


## Architecture and Design Patterns

**Repository Pattern** — `DatabaseManager` encapsulates all data access. The rest of the app never writes SQL directly. All business rules live inside this class.

**Decorator Pattern** — `@require_role("station_admin")` is a higher-order function that enforces access control at the function level. This is Layer 2 of the RBAC system.

**Separation of Concerns** — Views only display. All business rules including booking validation, suspension logic and slot generation live in `DatabaseManager.validate_booking_request()`.

**Lazy Evaluation** — No background scheduler needed. `cleanup_expired()` runs on every page load, marking no-shows, expiring waitlists and resetting 6-month counters.

**Singleton via Cache** — `@st.cache_resource` on `get_db()` ensures only one `DatabaseManager` instance exists across all Streamlit reruns.

---

## Security

- Passwords hashed with bcrypt at rounds=12. Plain text never stored at any point.
- Two-layer RBAC: tab visibility (Layer 1) and `require_role` decorator (Layer 2).
- Login accepts email or driver's license. Same generic error message for both to prevent account enumeration.
- Government official interface completely separate from public segments. No crossover.
- Email credentials stored in Streamlit Secrets, never in source code.

---

The database reseeds automatically whenever Streamlit Cloud restarts the container.

---

## Key Business Rules

**Fuel availability** is always calculated dynamically as stock minus active bookings minus soft reserved. Never stored as a column.

**One booking per vehicle per day** — enforced by license plate, not driver's license. A driver with two vehicles can book each independently.

**No-show definition** — a booking not serviced by midnight of the appointment day. Late same-day arrivals are not no-shows. Token remains valid all day.

**Cancellation tiers** — cancel 2 or more hours before: no consequence. Cancel under 2 hours: 24 hour ban for 1st offence, 72 hours for 2nd, 1 week for 3rd. Counts reset on the 1st of each month.

**Postponement** — maximum 3 successful postponements per calendar month. No penalty ever for postponing. If no slots available, user joins postponement waitlist and original booking stays active.

**Waitlist** — shown only when all slots are taken. One entry per vehicle per day. Offers sent during operating hours only with a 30-minute acceptance window. Soft reserve applied during offer window.

**Price locking** — advance booking price locked at booking creation time. Walk-in price locked at admin approval time. Price changes by government never affect existing bookings.

**Ride share plates** — motorcycles registered as ride-share must use the RS- plate prefix. Cross-validated against vehicle type at booking time.

---

## Acknowledgements

Built as a course project.

Fuel pricing based on Bangladesh Petroleum Corporation rates (2024).
Load shedding schedule structure based on Power Development Board publicly available outage reporting format.
