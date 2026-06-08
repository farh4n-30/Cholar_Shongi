import sqlite3
import os
import bcrypt
from datetime import datetime, timedelta, date
import random
import string

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "cholar_shongi.db"
)


class DatabaseManager:

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._create_all_tables()
        self._seed_if_empty()


    def _create_all_tables(self):
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name               TEXT NOT NULL,
                email                   TEXT UNIQUE NOT NULL,
                password_hash           TEXT NOT NULL,
                role                    TEXT NOT NULL,
                driver_license          TEXT UNIQUE NOT NULL,
                assigned_city           TEXT,
                station_id              INTEGER,
                no_show_count_lifetime  INTEGER DEFAULT 0,
                no_show_count_6months   INTEGER DEFAULT 0,
                short_cancel_count      INTEGER DEFAULT 0,
                warning_count           INTEGER DEFAULT 0,
                postpone_count_month    INTEGER DEFAULT 0,
                is_flagged              INTEGER DEFAULT 0,
                force_password_change   INTEGER DEFAULT 0,
                created_at              TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id                     INTEGER PRIMARY KEY AUTOINCREMENT,
                name                   TEXT NOT NULL,
                city                   TEXT NOT NULL,
                area                   TEXT NOT NULL,
                address                TEXT NOT NULL,
                octane_stock           REAL DEFAULT 0,
                diesel_stock           REAL DEFAULT 0,
                petrol_stock           REAL DEFAULT 0,
                kerosene_stock         REAL DEFAULT 0,
                octane_capacity        REAL DEFAULT 5000,
                diesel_capacity        REAL DEFAULT 5000,
                petrol_capacity        REAL DEFAULT 3000,
                kerosene_capacity      REAL DEFAULT 2000,
                octane_soft_reserved   REAL DEFAULT 0,
                diesel_soft_reserved   REAL DEFAULT 0,
                petrol_soft_reserved   REAL DEFAULT 0,
                kerosene_soft_reserved REAL DEFAULT 0,
                is_active              INTEGER DEFAULT 1
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS station_schedule (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id                  INTEGER NOT NULL UNIQUE,
                opening_time                TEXT NOT NULL,
                closing_time                TEXT NOT NULL,
                online_cutoff_time          TEXT NOT NULL,
                slot_duration_motorcycle    INTEGER DEFAULT 4,
                slot_duration_motorcycle_rs INTEGER DEFAULT 4,
                slot_duration_cng_auto      INTEGER DEFAULT 5,
                slot_duration_sedan         INTEGER DEFAULT 6,
                slot_duration_suv           INTEGER DEFAULT 7,
                slot_duration_microbus      INTEGER DEFAULT 8,
                slot_duration_truck         INTEGER DEFAULT 12,
                slot_duration_bus           INTEGER DEFAULT 15,
                pump_count                  INTEGER DEFAULT 2,
                daily_cap                   INTEGER DEFAULT 80,
                walkin_enabled              INTEGER DEFAULT 1,
                FOREIGN KEY (station_id) REFERENCES stations(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS feeders (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                area TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS load_shedding (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                feeder_id      INTEGER NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime   TEXT NOT NULL,
                internal_note  TEXT,
                published_by   INTEGER NOT NULL,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feeder_id)    REFERENCES feeders(id),
                FOREIGN KEY (published_by) REFERENCES users(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                token            TEXT UNIQUE NOT NULL,
                user_id          INTEGER NOT NULL,
                station_id       INTEGER NOT NULL,
                booking_type     TEXT NOT NULL,
                vehicle_type     TEXT NOT NULL,
                fuel_type        TEXT NOT NULL,
                license_plate    TEXT NOT NULL,
                driver_license   TEXT NOT NULL,
                full_name        TEXT NOT NULL,
                email            TEXT NOT NULL,
                requested_amount REAL NOT NULL,
                actual_dispensed REAL,
                price_per_litre  REAL NOT NULL,
                estimated_cost   REAL NOT NULL,
                actual_cost      REAL,
                booking_purpose  TEXT,
                status           TEXT DEFAULT 'scheduled',
                slot_datetime    TEXT,
                serviced_at      TEXT,
                postpone_count   INTEGER DEFAULT 0,
                month_year       TEXT,
                pending_postpone INTEGER DEFAULT 0,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id)    REFERENCES users(id),
                FOREIGN KEY (station_id) REFERENCES stations(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_limit_rules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_type TEXT NOT NULL,
                fuel_type    TEXT NOT NULL,
                max_litres   REAL NOT NULL,
                set_by       INTEGER NOT NULL,
                updated_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(vehicle_type, fuel_type)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS fuel_prices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                fuel_type       TEXT UNIQUE NOT NULL,
                price_per_litre REAL NOT NULL,
                set_by          INTEGER NOT NULL,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS license_restrictions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                restriction_type TEXT NOT NULL,
                value            TEXT NOT NULL,
                max_bookings     INTEGER NOT NULL,
                period_hours     INTEGER NOT NULL,
                set_by           INTEGER NOT NULL,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id             INTEGER NOT NULL,
                station_id          INTEGER NOT NULL,
                fuel_type           TEXT NOT NULL,
                vehicle_type        TEXT NOT NULL,
                license_plate       TEXT NOT NULL,
                requested_amount    REAL NOT NULL,
                waitlist_type       TEXT DEFAULT 'advance',
                original_booking_id INTEGER,
                status              TEXT DEFAULT 'waiting',
                offer_expires_at    TEXT,
                joined_at           TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at          TEXT NOT NULL,
                FOREIGN KEY (user_id)    REFERENCES users(id),
                FOREIGN KEY (station_id) REFERENCES stations(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS postpone_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id     INTEGER NOT NULL,
                driver_license TEXT NOT NULL,
                original_slot  TEXT NOT NULL,
                new_slot       TEXT NOT NULL,
                postponed_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                month_year     TEXT NOT NULL,
                FOREIGN KEY (booking_id) REFERENCES bookings(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS suspensions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                driver_license  TEXT NOT NULL,
                suspension_type TEXT NOT NULL,
                reason          TEXT NOT NULL,
                suspended_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                suspended_until TEXT NOT NULL,
                is_active       INTEGER DEFAULT 1,
                lifted_by       INTEGER,
                lift_note       TEXT,
                lifted_at       TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT NOT NULL,
                message      TEXT NOT NULL,
                published_by INTEGER NOT NULL,
                published_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at   TEXT NOT NULL,
                is_active    INTEGER DEFAULT 1
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                role      TEXT NOT NULL,
                action    TEXT NOT NULL,
                details   TEXT,
                log_type  TEXT DEFAULT 'fuel',
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS emergency_log (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                token               TEXT UNIQUE NOT NULL,
                registration_number TEXT NOT NULL,
                vehicle_category    TEXT NOT NULL,
                organisation        TEXT NOT NULL,
                station_id          INTEGER NOT NULL,
                driver_license      TEXT NOT NULL,
                fuel_type           TEXT NOT NULL,
                requested_amount    REAL NOT NULL,
                actual_dispensed    REAL,
                price_per_litre     REAL NOT NULL,
                eta_minutes         INTEGER NOT NULL,
                eta_datetime        TEXT NOT NULL,
                status              TEXT DEFAULT 'scheduled',
                serviced_at         TEXT,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (station_id) REFERENCES stations(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS special_vehicles (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_number TEXT UNIQUE NOT NULL,
                vehicle_category    TEXT NOT NULL,
                organisation        TEXT NOT NULL,
                is_active           INTEGER DEFAULT 1,
                registered_by       INTEGER NOT NULL,
                created_at          TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS special_vehicle_eligibility (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_category TEXT UNIQUE NOT NULL,
                is_enabled       INTEGER DEFAULT 0,
                set_by           INTEGER,
                updated_at       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS resupply_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id     INTEGER NOT NULL,
                fuel_type      TEXT NOT NULL,
                quantity_added REAL NOT NULL,
                logged_by      INTEGER NOT NULL,
                logged_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (station_id) REFERENCES stations(id)
            )
        """)

        self.conn.commit()

    def _seed_if_empty(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] > 0:
            return
        self._seed_users()
        self._seed_stations()
        self._seed_feeders()
        self._seed_load_shedding()
        self._seed_fuel_prices()
        self._seed_daily_limits()
        self._seed_special_vehicles()
        self._seed_announcements()
        self._seed_bookings()
        self._seed_emergency_bookings()
        self._seed_waitlist()
        self._seed_suspensions()
        self._seed_resupply_log()
        self._seed_audit_log()
        self.conn.commit()

    def _hp(self, pw):
        return bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(rounds=12))

    def _fmt(self, dt):
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _seed_users(self):
        c = self.conn.cursor()
        rows = [
            ("Md. Kamal Hossain",   "govt@bangladesh.gov.bd",   "govt2024",    "government_official", "DL-GOV-0001-2019", None,         None),
            ("Engr. Rafiqul Islam", "pdb.dhaka@pdb.gov.bd",     "pdbdhaka24",  "pdb_admin",           "DL-PDB-0001-2018", "Dhaka",      None),
            ("Engr. Sohel Rana",    "pdb.ctg@pdb.gov.bd",       "pdbctg2024",  "pdb_admin",           "DL-PDB-0002-2018", "Chattogram", None),
            ("Gulshan Station 1",   "admin@gulshan1.fuel.bd",   "station2024", "station_admin",       "DL-STN-0001-2020", None,         1),
            ("Dhanmondi Station",   "admin@dhanmondi1.fuel.bd", "station2024", "station_admin",       "DL-STN-0002-2020", None,         2),
            ("Agrabad Station 1",   "admin@agrabad1.fuel.bd",   "station2024", "station_admin",       "DL-STN-0003-2020", None,         3),
            ("Md. Rahim Uddin",     "rahim.uddin@gmail.com",    "user2024",    "user",                "DL-DHK-2341-2021", None,         None),
            ("Md. Karim Miah",      "karim.miah@gmail.com",     "user2024",    "user",                "DL-DHK-5672-2020", None,         None),
            ("Fatima Begum",        "fatima.begum@gmail.com",   "user2024",    "user",                "DL-CTG-8912-2022", None,         None),
            ("Nusrat Jahan",        "nusrat.jahan@gmail.com",   "user2024",    "user",                "DL-CTG-1122-2021", None,         None),
        ]
        for r in rows:
            c.execute("""
                INSERT INTO users
                (full_name, email, password_hash, role, driver_license,
                 assigned_city, station_id)
                VALUES (?,?,?,?,?,?,?)
            """, (r[0], r[1], self._hp(r[2]), r[3], r[4], r[5], r[6]))

    def _seed_stations(self):
        c = self.conn.cursor()
        stations = [
            ("Gulshan Filling Station",   "Dhaka",      "Gulshan",     "Road 11, Gulshan-1, Dhaka-1212",         4200, 3800, 2100, 1800, 6000, 6000, 4000, 3000),
            ("Dhanmondi Service Station", "Dhaka",      "Dhanmondi",   "Road 27, Dhanmondi, Dhaka-1209",          480, 4500,  290, 1200, 4000, 6000, 3000, 2000),
            ("Agrabad Energy Point",      "Chattogram", "Agrabad",     "Agrabad C/A, Chattogram-4100",           2900, 3100, 2700,  900, 4000, 5000, 4000, 2000),
            ("Banani Fuel Point",         "Dhaka",      "Banani",      "Road 6, Block A, Banani, Dhaka-1213",    3900, 4100, 1800, 1500, 5000, 6000, 3000, 2000),
            ("Mirpur Energy Hub",         "Dhaka",      "Mirpur",      "Section 10, Mirpur, Dhaka-1216",         4800, 4700, 4900, 2200, 6000, 6000, 6000, 3000),
            ("Uttara Fuel Station",       "Dhaka",      "Uttara",      "Sector 7, Uttara, Dhaka-1230",           3200, 3600, 2800, 1100, 5000, 5000, 4000, 2000),
            ("Badda Filling Point",       "Dhaka",      "Badda",       "Middle Badda, Dhaka-1212",               1100,  800,  950,  400, 3000, 3000, 2000, 1500),
            ("Mohammadpur Fuel Station",  "Dhaka",      "Mohammadpur", "Asad Gate, Mohammadpur, Dhaka-1207",     4100, 3900, 3700, 1600, 5000, 5000, 5000, 2500),
            ("Nasirabad Fuel Hub",        "Chattogram", "Nasirabad",   "Nasirabad Housing, Chattogram-4210",     3700, 4200, 3100, 1400, 5000, 6000, 4000, 2000),
            ("Chandgaon Service Station", "Chattogram", "Chandgaon",   "Chandgaon R/A, Chattogram-4212",         4400, 4600, 4200, 1900, 6000, 6000, 6000, 3000),
            ("GEC Filling Station",       "Chattogram", "GEC",         "GEC Circle, Chattogram-4000",             200,  150,    0,  300, 2000, 2000, 1500, 1000),
            ("Halishahar Fuel Point",     "Chattogram", "Halishahar",  "Port Connecting Road, Chattogram-4204",  3800, 4100, 3500, 1700, 5000, 6000, 5000, 2500),
            ("Khulshi Premium Fuel",      "Chattogram", "Khulshi",     "Khulshi R/A, Chattogram-4225",           4900, 4800, 4700, 2100, 6000, 6000, 6000, 3000),
        ]
        for s in stations:
            c.execute("""
                INSERT INTO stations
                (name, city, area, address,
                 octane_stock, diesel_stock, petrol_stock, kerosene_stock,
                 octane_capacity, diesel_capacity, petrol_capacity, kerosene_capacity)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, s)

        schedules = [
            (1,  "07:00", "21:00", "20:00", 4, 1),
            (2,  "07:00", "21:00", "20:00", 3, 1),
            (3,  "08:00", "20:00", "19:00", 3, 0),
            (4,  "08:00", "20:00", "19:00", 3, 1),
            (5,  "07:00", "21:00", "20:00", 4, 1),
            (6,  "08:00", "20:00", "19:00", 3, 1),
            (7,  "08:00", "18:00", "17:00", 2, 0),
            (8,  "08:00", "20:00", "19:00", 3, 1),
            (9,  "08:00", "20:00", "19:00", 3, 1),
            (10, "07:00", "21:00", "20:00", 4, 1),
            (11, "08:00", "18:00", "17:00", 2, 0),
            (12, "08:00", "20:00", "19:00", 3, 1),
            (13, "07:00", "22:00", "21:00", 4, 1),
        ]
        for s in schedules:
            c.execute("""
                INSERT INTO station_schedule
                (station_id, opening_time, closing_time,
                 online_cutoff_time, pump_count, walkin_enabled)
                VALUES (?,?,?,?,?,?)
            """, s)

    def _seed_feeders(self):
        c = self.conn.cursor()
        feeders = [
            ("Gulshan Feeder A",     "Dhaka",      "Gulshan"),
            ("Banani Feeder B",      "Dhaka",      "Banani"),
            ("Dhanmondi Feeder C",   "Dhaka",      "Dhanmondi"),
            ("Mirpur Feeder D",      "Dhaka",      "Mirpur"),
            ("Uttara Feeder E",      "Dhaka",      "Uttara"),
            ("Badda Feeder F",       "Dhaka",      "Badda"),
            ("Mohammadpur Feeder G", "Dhaka",      "Mohammadpur"),
            ("Nasirabad Feeder H",   "Chattogram", "Nasirabad"),
            ("Chandgaon Feeder I",   "Chattogram", "Chandgaon"),
            ("Agrabad Feeder J",     "Chattogram", "Agrabad"),
            ("GEC Feeder K",         "Chattogram", "GEC"),
            ("Halishahar Feeder L",  "Chattogram", "Halishahar"),
            ("Khulshi Feeder M",     "Chattogram", "Khulshi"),
        ]
        for f in feeders:
            c.execute(
                "INSERT INTO feeders (name, city, area) VALUES (?,?,?)", f
            )

    def _seed_load_shedding(self):
        c = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt

        rows = [
            (1, f(now-timedelta(hours=1)),    f(now+timedelta(hours=1)),    "Routine maintenance",   2, -48, True),
            (4, f(now-timedelta(minutes=30)), f(now+timedelta(minutes=90)), "Emergency grid repair", 2, -48, False),
            (6, f(now-timedelta(hours=2)),    f(now+timedelta(minutes=30)), "Scheduled maintenance", 2, -48, False),
            (2, f(now+timedelta(hours=2)),    f(now+timedelta(hours=4)),    "Planned outage",        2, -24, False),
            (3, f(now+timedelta(hours=3)),    f(now+timedelta(hours=5)),    "Transformer work",      2, -24, False),
            (5, f(now+timedelta(hours=5)),    f(now+timedelta(hours=7)),    "Line maintenance",      2, -24, False),
            (7, f(now+timedelta(hours=6)),    f(now+timedelta(hours=8)),    "Substation upgrade",    2, -24, False),
            (8,  f(now-timedelta(hours=5)),  f(now-timedelta(hours=3)),    "Completed maintenance", 3, -72, False),
            (9,  f(now-timedelta(hours=8)),  f(now-timedelta(hours=6)),    "Emergency repair done", 3, -72, False),
            (10, f(now-timedelta(hours=10)), f(now-timedelta(hours=8)),    "Routine check done",    3, -72, False),
        ]
        for row in rows:
            fid, start, end, note, pub, created_offset, edited = row
            created = f(now + timedelta(hours=created_offset))
            updated = f(now - timedelta(hours=6)) if edited else created
            c.execute("""
                INSERT INTO load_shedding
                (feeder_id, start_datetime, end_datetime, internal_note,
                 published_by, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?)
            """, (fid, start, end, note, pub, created, updated))

    def _seed_fuel_prices(self):
        c = self.conn.cursor()
        for fuel, price in [
            ("Octane",   125.0),
            ("Diesel",   109.0),
            ("Petrol",   122.0),
            ("Kerosene", 107.0),
        ]:
            c.execute("""
                INSERT INTO fuel_prices (fuel_type, price_per_litre, set_by)
                VALUES (?,?,1)
            """, (fuel, price))

    def _seed_daily_limits(self):
        c = self.conn.cursor()
        limits = {
            "Motorcycle (Personal)":   {"Octane": 5,   "Diesel": 5,   "Petrol": 5,   "Kerosene": 5},
            "Motorcycle (Ride Share)": {"Octane": 10,  "Diesel": 10,  "Petrol": 10,  "Kerosene": 10},
            "CNG Auto":                {"Octane": 20,  "Diesel": 20,  "Petrol": 20,  "Kerosene": 20},
            "Sedan":                   {"Octane": 40,  "Diesel": 45,  "Petrol": 40,  "Kerosene": 40},
            "SUV":                     {"Octane": 60,  "Diesel": 65,  "Petrol": 60,  "Kerosene": 60},
            "Microbus":                {"Octane": 60,  "Diesel": 65,  "Petrol": 60,  "Kerosene": 60},
            "Truck":                   {"Octane": 100, "Diesel": 120, "Petrol": 100, "Kerosene": 100},
            "Bus":                     {"Octane": 120, "Diesel": 150, "Petrol": 120, "Kerosene": 120},
        }
        for vt, fuel_map in limits.items():
            for ft, ml in fuel_map.items():
                c.execute("""
                    INSERT OR IGNORE INTO daily_limit_rules
                    (vehicle_type, fuel_type, max_litres, set_by)
                    VALUES (?,?,?,1)
                """, (vt, ft, ml))

    def _seed_special_vehicles(self):
        c = self.conn.cursor()
        for cat, enabled in [
            ("ambulance",  1),
            ("fire",       1),
            ("police",     0),
            ("government", 0),
            ("military",   0),
        ]:
            c.execute("""
                INSERT INTO special_vehicle_eligibility
                (vehicle_category, is_enabled, set_by)
                VALUES (?,?,1)
            """, (cat, enabled))

        vehicles = [
            ("FIRE-DHK-001", "fire",       "Dhaka Fire Service"),
            ("FIRE-CTG-001", "fire",       "Chattogram Fire Service"),
            ("AMB-DHK-001",  "ambulance",  "Dhaka Medical College Hospital"),
            ("AMB-CTG-001",  "ambulance",  "Chattogram General Hospital"),
            ("POL-DHK-001",  "police",     "DMP"),
            ("GOVT-BD-001",  "government", "Prime Minister's Office"),
        ]
        for v in vehicles:
            c.execute("""
                INSERT INTO special_vehicles
                (registration_number, vehicle_category, organisation,
                 is_active, registered_by)
                VALUES (?,?,?,1,1)
            """, v)

    def _seed_announcements(self):
        c = self.conn.cursor()
        now = datetime.now()
        rows = [
            (
                "Eid Holiday Fuel Notice",
                "Fuel rationing is in effect during Eid holidays. Plan accordingly.",
                1,
                self._fmt(now - timedelta(days=2)),
                self._fmt(now + timedelta(days=5)),
            ),
            (
                "Load Shedding Advisory",
                "Increased load shedding expected this week due to grid maintenance.",
                1,
                self._fmt(now - timedelta(days=1)),
                self._fmt(now + timedelta(days=4)),
            ),
        ]
        for r in rows:
            c.execute("""
                INSERT INTO announcements
                (title, message, published_by, published_at, expires_at)
                VALUES (?,?,?,?,?)
            """, r)

    def _seed_bookings(self):
        c  = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt
        my  = now.strftime("%Y-%m")

        def ins(token, uid, sid, btype, vtype, ftype,
                plate, dl, name, email, req, actual, price,
                status, slot_dt, serv_at=None):
            est = req * price
            act = (actual * price) if actual else None
            c.execute("""
                INSERT OR IGNORE INTO bookings
                (token, user_id, station_id, booking_type, vehicle_type,
                 fuel_type, license_plate, driver_license, full_name, email,
                 requested_amount, actual_dispensed, price_per_litre,
                 estimated_cost, actual_cost, status, slot_datetime,
                 serviced_at, month_year)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (token, uid, sid, btype, vtype, ftype, plate, dl, name,
                  email, req, actual, price, est, act, status,
                  slot_dt, serv_at, my))

        ins("A1B2C3D4", 7, 1,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",38,38,125.0,"serviced",f(now-timedelta(days=7,hours=9)),f(now-timedelta(days=7,hours=8,minutes=56)))
        ins("E5F6G7H8", 8, 1,"advance","SUV","Octane","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",55,53,125.0,"serviced",f(now-timedelta(days=7,hours=10)),f(now-timedelta(days=7,hours=9,minutes=52)))
        ins("I9J0K1L2", 9, 1,"advance","Sedan","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",42,42,109.0,"serviced",f(now-timedelta(days=6,hours=9)),f(now-timedelta(days=6,hours=8,minutes=53)))
        ins("M3N4O5P6",10, 1,"advance","Bus","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",140,138,109.0,"serviced",f(now-timedelta(days=6,hours=11)),f(now-timedelta(days=6,hours=10,minutes=45)))
        ins("Q7R8S9T0", 7, 1,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",40,40,125.0,"serviced",f(now-timedelta(days=5,hours=9)),f(now-timedelta(days=5,hours=8,minutes=53)))
        ins("U1V2W3X4", 8, 1,"advance","Motorcycle (Personal)","Octane","DHAKA-METRO-KA-05-1122","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",4,4,125.0,"serviced",f(now-timedelta(days=5,hours=11)),f(now-timedelta(days=5,hours=10,minutes=56)))
        ins("Y5Z6A7B8", 9, 1,"advance","Sedan","Octane","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",35,33,125.0,"serviced",f(now-timedelta(days=4,hours=14)),f(now-timedelta(days=4,hours=13,minutes=53)))
        ins("C9D0E1F2",10, 1,"advance","Truck","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",115,115,109.0,"serviced",f(now-timedelta(days=4,hours=10)),f(now-timedelta(days=4,hours=9,minutes=48)))
        ins("G3H4I5J6", 7, 1,"advance","Sedan","Petrol","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",38,36,122.0,"serviced",f(now-timedelta(days=3,hours=15)),f(now-timedelta(days=3,hours=14,minutes=53)))
        ins("K7L8M9N0", 8, 1,"advance","SUV","Diesel","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",60,58,109.0,"serviced",f(now-timedelta(days=3,hours=16)),f(now-timedelta(days=3,hours=15,minutes=52)))
        ins("O1P2Q3R4", 7, 1,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",40,40,125.0,"serviced",f(now-timedelta(days=2,hours=9)),f(now-timedelta(days=2,hours=8,minutes=53)))
        ins("S5T6U7V8", 9, 1,"advance","Sedan","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",44,44,109.0,"serviced",f(now-timedelta(days=2,hours=11)),f(now-timedelta(days=2,hours=10,minutes=53)))
        ins("W9X0Y1Z2",10, 1,"advance","Motorcycle (Personal)","Petrol","CTG-METRO-KA-07-2211","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",5,5,122.0,"serviced",f(now-timedelta(days=1,hours=10)),f(now-timedelta(days=1,hours=9,minutes=56)))
        ins("A3B4C5D6", 8, 1,"advance","SUV","Octane","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",55,53,125.0,"serviced",f(now-timedelta(days=1,hours=14)),f(now-timedelta(days=1,hours=13,minutes=52)))
        ins("E7F8G9H0", 7, 1,"advance","Truck","Diesel","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",118,118,109.0,"serviced",f(now-timedelta(days=1,hours=16)),f(now-timedelta(days=1,hours=15,minutes=47)))
        ins("I1J2K3L4", 7, 1,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",35,None,125.0,"scheduled",f(now+timedelta(hours=3)))
        ins("M5N6O7P8", 8, 1,"advance","Motorcycle (Ride Share)","Octane","RS-DHAKA-KA-12-3344","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",8,None,125.0,"scheduled",f(now+timedelta(hours=3,minutes=15)))
        ins("Q9R0S1T2", 9, 1,"advance","Sedan","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",42,None,109.0,"scheduled",f(now+timedelta(hours=4)))
        ins("U3V4W5X6",10, 1,"advance","SUV","Petrol","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",55,None,122.0,"scheduled",f(now+timedelta(days=1,hours=9)))
        ins("Y7Z8A9B0", 7, 1,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",40,None,125.0,"scheduled",f(now+timedelta(days=1,hours=10)))
        ins("C1D2E3F4", 8, 1,"advance","SUV","Octane","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",55,None,125.0,"no_show",f(now-timedelta(days=10,hours=9)))
        ins("G5H6I7J8", 8, 1,"advance","Motorcycle (Personal)","Petrol","DHAKA-METRO-KA-12-3344","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",4,None,122.0,"no_show",f(now-timedelta(days=8,hours=9)))
        ins("K9L0M1N2", 9, 1,"advance","Sedan","Octane","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",40,None,125.0,"cancelled",f(now-timedelta(days=3,hours=9)))
        ins("O3P4Q5R6",10, 1,"advance","SUV","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",55,None,109.0,"cancelled",f(now-timedelta(days=1,hours=14)))
        ins("WI000001", 7, 1,"walkin","Sedan","Diesel","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",35,None,109.0,"pending_approval",f(now-timedelta(minutes=15)))
        ins("T1U2V3W4", 7, 2,"advance","Sedan","Diesel","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",44,44,109.0,"serviced",f(now-timedelta(days=6,hours=8)),f(now-timedelta(days=6,hours=7,minutes=53)))
        ins("X5Y6Z7A8", 8, 2,"advance","SUV","Diesel","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",60,58,109.0,"serviced",f(now-timedelta(days=6,hours=9)),f(now-timedelta(days=6,hours=8,minutes=52)))
        ins("B9C0D1E2", 9, 2,"advance","Truck","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",119,119,109.0,"serviced",f(now-timedelta(days=5,hours=10)),f(now-timedelta(days=5,hours=9,minutes=48)))
        ins("F3G4H5I6",10, 2,"advance","Sedan","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",45,45,109.0,"serviced",f(now-timedelta(days=5,hours=14)),f(now-timedelta(days=5,hours=13,minutes=53)))
        ins("J7K8L9M0", 7, 2,"advance","Sedan","Diesel","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",43,43,109.0,"serviced",f(now-timedelta(days=4,hours=9)),f(now-timedelta(days=4,hours=8,minutes=53)))
        ins("N1O2P3Q4", 8, 2,"advance","SUV","Kerosene","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",55,53,107.0,"serviced",f(now-timedelta(days=3,hours=11)),f(now-timedelta(days=3,hours=10,minutes=52)))
        ins("R5S6T7U8", 9, 2,"advance","Bus","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",148,148,109.0,"serviced",f(now-timedelta(days=2,hours=8)),f(now-timedelta(days=2,hours=7,minutes=45)))
        ins("V9W0X1Y2",10, 2,"advance","Sedan","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",42,42,109.0,"serviced",f(now-timedelta(days=1,hours=15)),f(now-timedelta(days=1,hours=14,minutes=53)))
        ins("Z3A4B5C6", 9, 2,"advance","Sedan","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",45,None,109.0,"scheduled",f(now+timedelta(hours=2)))
        ins("D7E8F9G0",10, 2,"advance","Truck","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",120,None,109.0,"scheduled",f(now+timedelta(hours=2,minutes=30)))
        ins("H1I2J3K4", 7, 2,"advance","Sedan","Diesel","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",43,None,109.0,"scheduled",f(now+timedelta(hours=5)))
        ins("L5M6N7O8", 8, 2,"advance","SUV","Kerosene","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",55,None,107.0,"scheduled",f(now+timedelta(hours=5,minutes=30)))
        ins("P9Q0R1S2", 7, 2,"advance","SUV","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",55,None,125.0,"no_show",f(now-timedelta(days=9,hours=9)))
        ins("T3U4V5W6", 8, 2,"advance","Sedan","Octane","DHAKA-METRO-GA-44-5566","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",38,None,125.0,"no_show",f(now-timedelta(days=8,hours=9)))
        ins("X7Y8Z9A0", 9, 2,"advance","Sedan","Petrol","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",36,None,122.0,"no_show",f(now-timedelta(days=7,hours=9)))
        ins("B1C2D3E4",10, 2,"advance","Motorcycle (Personal)","Octane","CTG-METRO-KA-07-2211","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",5,None,125.0,"no_show",f(now-timedelta(days=6,hours=9)))
        ins("F5G6H7I8", 7, 2,"advance","Sedan","Octane","DHAKA-METRO-GA-11-2233","DL-DHK-2341-2021","Md. Rahim Uddin","rahim.uddin@gmail.com",40,None,125.0,"cancelled",f(now-timedelta(days=5,hours=9)))
        ins("J9K0L1M2", 8, 2,"advance","Motorcycle (Personal)","Petrol","DHAKA-METRO-KA-05-1122","DL-DHK-5672-2020","Md. Karim Miah","karim.miah@gmail.com",4,None,122.0,"cancelled",f(now-timedelta(days=4,hours=9)))
        ins("N3O4P5Q6", 9, 2,"advance","Sedan","Petrol","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",36,None,122.0,"cancelled",f(now-timedelta(days=3,hours=9)))
        ins("R7S8T9U0",10, 2,"advance","SUV","Octane","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",55,None,125.0,"cancelled",f(now-timedelta(days=2,hours=9)))
        ins("V1W2X3Y4", 9, 3,"advance","Sedan","Octane","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",38,38,125.0,"serviced",f(now-timedelta(days=7,hours=9)),f(now-timedelta(days=7,hours=8,minutes=53)))
        ins("Z5A6B7C8",10, 3,"advance","SUV","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",60,58,109.0,"serviced",f(now-timedelta(days=6,hours=10)),f(now-timedelta(days=6,hours=9,minutes=52)))
        ins("D9E0F1G2", 9, 3,"advance","Truck","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",116,116,109.0,"serviced",f(now-timedelta(days=5,hours=11)),f(now-timedelta(days=5,hours=9,minutes=48)))
        ins("H3I4J5K6",10, 3,"advance","Sedan","Petrol","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",37,35,122.0,"serviced",f(now-timedelta(days=4,hours=14)),f(now-timedelta(days=4,hours=13,minutes=53)))
        ins("L7M8N9O0", 9, 3,"advance","Sedan","Octane","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",40,40,125.0,"serviced",f(now-timedelta(days=3,hours=9)),f(now-timedelta(days=3,hours=8,minutes=53)))
        ins("P1Q2R3S4",10, 3,"advance","Motorcycle (Personal)","Petrol","CTG-METRO-KA-07-2211","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",5,5,122.0,"serviced",f(now-timedelta(days=2,hours=11)),f(now-timedelta(days=2,hours=10,minutes=56)))
        ins("T5U6V7W8", 9, 3,"advance","SUV","Kerosene","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",55,53,107.0,"serviced",f(now-timedelta(days=1,hours=15)),f(now-timedelta(days=1,hours=14,minutes=52)))
        ins("X9Y0Z1A2",10, 3,"advance","Sedan","Octane","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",38,None,125.0,"scheduled",f(now+timedelta(hours=2)))
        ins("B3C4D5E6", 9, 3,"advance","SUV","Diesel","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",60,None,109.0,"scheduled",f(now+timedelta(hours=3)))
        ins("F7G8H9I0",10, 3,"advance","Truck","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",115,None,109.0,"scheduled",f(now+timedelta(days=1,hours=9)))
        ins("J1K2L3M4", 9, 3,"advance","Sedan","Petrol","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",36,None,122.0,"scheduled",f(now+timedelta(days=1,hours=10)))
        ins("N5O6P7Q8",10, 3,"advance","SUV","Octane","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",55,None,125.0,"no_show",f(now-timedelta(days=5,hours=9)))
        ins("R9S0T1U2", 9, 3,"advance","Sedan","Petrol","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",37,None,122.0,"no_show",f(now-timedelta(days=4,hours=9)))
        ins("V3W4X5Y6",10, 3,"advance","Sedan","Diesel","CTG-METRO-BA-33-6677","DL-CTG-1122-2021","Nusrat Jahan","nusrat.jahan@gmail.com",44,None,109.0,"cancelled",f(now-timedelta(days=3,hours=9)))
        ins("Z7A8B9C0", 9, 3,"advance","Motorcycle (Personal)","Octane","CTG-METRO-TA-22-4455","DL-CTG-8912-2022","Fatima Begum","fatima.begum@gmail.com",5,None,125.0,"cancelled",f(now-timedelta(days=2,hours=9)))

        self.conn.commit()

    def _seed_emergency_bookings(self):
        c   = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt
        rows = [
            ("EX-A1B2C3","AMB-DHK-001","ambulance","Dhaka Medical College Hospital",1,"DL-GOV-0001-2019","Octane", 45, 45, 125.0,10,f(now-timedelta(days=3,hours=9,minutes=14)),"serviced",f(now-timedelta(days=3,hours=9,minutes=2))),
            ("EX-E5F6G7","FIRE-CTG-001","fire","Chattogram Fire Service",          3,"DL-PDB-0002-2018","Diesel",180,175, 109.0,15,f(now-timedelta(days=2,hours=11,minutes=32)),"serviced",f(now-timedelta(days=2,hours=11,minutes=14))),
            ("EX-I9J0K1","AMB-CTG-001","ambulance","Chattogram General Hospital",  3,"DL-CTG-8912-2022","Octane", 40, 40, 125.0, 8,f(now-timedelta(days=1,hours=14,minutes=15)),"serviced",f(now-timedelta(days=1,hours=14,minutes=5))),
            ("EX-M3N4O5","FIRE-DHK-001","fire","Dhaka Fire Service",               1,"DL-DHK-2341-2021","Diesel",200,None,109.0,20,f(now+timedelta(minutes=20)),               "scheduled",None),
        ]
        for r in rows:
            (token,reg,cat,org,sid,dl,ftype,req,actual,
             price,eta_min,eta_dt,status,serv_at) = r
            c.execute("""
                INSERT OR IGNORE INTO emergency_log
                (token, registration_number, vehicle_category, organisation,
                 station_id, driver_license, fuel_type, requested_amount,
                 actual_dispensed, price_per_litre, eta_minutes,
                 eta_datetime, status, serviced_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (token,reg,cat,org,sid,dl,ftype,req,actual,
                  price,eta_min,eta_dt,status,serv_at))
        self.conn.commit()

    def _seed_waitlist(self):
        c   = self.conn.cursor()
        now = datetime.now()
        midnight = datetime.combine(
            date.today(), datetime.max.time()
        ).replace(microsecond=0)
        f = self._fmt

        rows = [
            (7,  2, "Octane", "Sedan", "DHAKA-METRO-GA-11-2233", 35, "advance",      None, f(midnight)),
            (9,  1, "Diesel", "Sedan", "CTG-METRO-TA-22-4455",   42, "postponement", None, f(now+timedelta(days=3))),
            (10, 1, "Octane", "SUV",   "CTG-METRO-BA-33-6677",   55, "advance",      None, f(midnight)),
        ]
        for r in rows:
            uid,sid,ftype,vtype,plate,amt,wtype,obid,exp = r
            c.execute("""
                INSERT INTO waitlist
                (user_id, station_id, fuel_type, vehicle_type,
                 license_plate, requested_amount, waitlist_type,
                 original_booking_id, expires_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (uid,sid,ftype,vtype,plate,amt,wtype,obid,exp))

    def _seed_suspensions(self):
        c   = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt

        rows = [
            (
                "DL-DHK-5672-2020", "no_show",
                "You missed 2 appointments without cancelling.",
                f(now-timedelta(days=3)),
                f(now+timedelta(days=4)),
                1
            ),
            (
                "DL-CTG-1122-2021", "late_cancellation",
                "You cancelled an appointment less than 2 hours "
                "before your scheduled slot.",
                f(now-timedelta(hours=12)),
                f(now+timedelta(hours=12)),
                1
            ),
        ]
        for r in rows:
            c.execute("""
                INSERT INTO suspensions
                (driver_license, suspension_type, reason,
                 suspended_at, suspended_until, is_active)
                VALUES (?,?,?,?,?,?)
            """, r)

        c.execute("""
            UPDATE users
            SET no_show_count_lifetime=2, no_show_count_6months=2
            WHERE driver_license='DL-DHK-5672-2020'
        """)

    def _seed_resupply_log(self):
        c   = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt

        rows = [
            (1, "Octane",   3000, 4, f(now-timedelta(days=4))),
            (1, "Diesel",   2000, 4, f(now-timedelta(days=2))),
            (1, "Petrol",   1500, 4, f(now-timedelta(days=3))),
            (3, "Diesel",   2000, 6, f(now-timedelta(days=5))),
            (3, "Octane",   1500, 6, f(now-timedelta(days=3))),
        ]
        for r in rows:
            sid, ftype, qty, logged_by, logged_at = r
            c.execute("""
                INSERT INTO resupply_log
                (station_id, fuel_type, quantity_added,
                 logged_by, logged_at)
                VALUES (?,?,?,?,?)
            """, (sid, ftype, qty, logged_by, logged_at))

    def _seed_audit_log(self):
        c   = self.conn.cursor()
        now = datetime.now()
        f   = self._fmt

        rows = [
            (1,"Md. Kamal Hossain","government_official","Set daily limit",       "Sedan + Octane = 40L",                "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set daily limit",       "Motorcycle (Personal) + Octane = 5L", "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set daily limit",       "Truck + Diesel = 120L",               "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set daily limit",       "Bus + Diesel = 150L",                 "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set fuel price",        "Octane: \u09f3125/L",                 "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set fuel price",        "Diesel: \u09f3109/L",                 "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set fuel price",        "Petrol: \u09f3122/L",                 "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Set fuel price",        "Kerosene: \u09f3107/L",               "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Enabled category",      "Ambulance — emergency bypass",        "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Enabled category",      "Fire Service — emergency bypass",     "fuel",        f(now-timedelta(days=3))),
            (1,"Md. Kamal Hossain","government_official","Published announcement","Eid Holiday Fuel Notice",             "fuel",        f(now-timedelta(days=2))),
            (2,"Engr. Rafiqul Islam","pdb_admin",        "Published schedule",    "Gulshan Feeder A — 2hr outage",       "electricity", f(now-timedelta(days=2))),
            (2,"Engr. Rafiqul Islam","pdb_admin",        "Edited schedule",       "Gulshan Feeder A — updated end time", "electricity", f(now-timedelta(hours=6))),
            (2,"Engr. Rafiqul Islam","pdb_admin",        "Published schedule",    "Mirpur Feeder D — 2hr outage",        "electricity", f(now-timedelta(days=2))),
            (3,"Engr. Sohel Rana",  "pdb_admin",        "Published schedule",    "Nasirabad Feeder H — maintenance",    "electricity", f(now-timedelta(days=2))),
            (3,"Engr. Sohel Rana",  "pdb_admin",        "Deleted schedule",      "Nasirabad Feeder H — expired",        "electricity", f(now-timedelta(days=1))),
            (4,"Gulshan Station 1", "station_admin",     "Marked as Serviced",    "Token A1B2C3D4 — 38L Octane",         "fuel",        f(now-timedelta(days=7,hours=8,minutes=56))),
            (4,"Gulshan Station 1", "station_admin",     "Marked as Serviced",    "Token E5F6G7H8 — 53L Octane",         "fuel",        f(now-timedelta(days=7,hours=9,minutes=52))),
            (4,"Gulshan Station 1", "station_admin",     "Walk-in approved",      "Sedan Diesel",                        "fuel",        f(now-timedelta(days=1,hours=14))),
            (4,"Gulshan Station 1", "station_admin",     "Logged resupply",       "+3000L Octane",                       "fuel",        f(now-timedelta(days=4))),
        ]
        for r in rows:
            c.execute("""
                INSERT INTO audit_log
                (user_id, user_name, role, action, details,
                 log_type, timestamp)
                VALUES (?,?,?,?,?,?,?)
            """, r)

    def get_user_by_email(self, email):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE email=?", (email,))
        return c.fetchone()

    def get_user_by_dl(self, dl):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE driver_license=?", (dl,))
        return c.fetchone()

    def get_user_by_id(self, uid):
        c = self.conn.cursor()
        c.execute("SELECT * FROM users WHERE id=?", (uid,))
        return c.fetchone()

    def create_user(self, full_name, email, password, driver_license):
        hashed = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        )
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO users
            (full_name, email, password_hash, role, driver_license)
            VALUES (?,?,?,?,?)
        """, (full_name, email, hashed, "user", driver_license))
        self.conn.commit()
        return c.lastrowid

    def verify_password(self, typed, stored_hash):
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        try:
            return bcrypt.checkpw(typed.encode("utf-8"), stored_hash)
        except Exception:
            return False

    def get_all_admins(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT id, full_name, email, role, station_id, assigned_city
            FROM users
            WHERE role IN ('station_admin','pdb_admin')
            ORDER BY role, full_name
        """)
        return c.fetchall()

    def reset_password(self, user_id, temp_password):
        hashed = bcrypt.hashpw(
            temp_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        )
        c = self.conn.cursor()
        c.execute("""
            UPDATE users
            SET password_hash=?, force_password_change=1
            WHERE id=?
        """, (hashed, user_id))
        self.conn.commit()

    def change_password(self, user_id, new_password):
        hashed = bcrypt.hashpw(
            new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)
        )
        c = self.conn.cursor()
        c.execute("""
            UPDATE users
            SET password_hash=?, force_password_change=0
            WHERE id=?
        """, (hashed, user_id))
        self.conn.commit()

    def get_all_cities(self):
        c = self.conn.cursor()
        c.execute("SELECT DISTINCT city FROM stations ORDER BY city")
        return [r[0] for r in c.fetchall()]

    def get_areas_by_city(self, city):
        c = self.conn.cursor()
        c.execute(
            "SELECT DISTINCT area FROM stations WHERE city=? ORDER BY area",
            (city,)
        )
        return [r[0] for r in c.fetchall()]

    def get_stations_by_area(self, city, area):
        c = self.conn.cursor()
        c.execute("""
            SELECT s.id,
                   s.name,
                   s.city,
                   s.area,
                   s.address,
                   s.octane_stock,
                   s.diesel_stock,
                   s.petrol_stock,
                   s.kerosene_stock,
                   s.octane_capacity,
                   s.diesel_capacity,
                   s.petrol_capacity,
                   s.kerosene_capacity,
                   s.octane_soft_reserved,
                   s.diesel_soft_reserved,
                   s.petrol_soft_reserved,
                   s.kerosene_soft_reserved,
                   s.is_active,
                   ss.id          AS schedule_id,
                   ss.opening_time,
                   ss.closing_time,
                   ss.online_cutoff_time,
                   ss.pump_count,
                   ss.walkin_enabled,
                   ss.daily_cap
            FROM stations s
            JOIN station_schedule ss ON ss.station_id = s.id
            WHERE s.city=? AND s.area=? AND s.is_active=1
        """, (city, area))
        return c.fetchall()

    def get_station_by_id(self, sid):
        c = self.conn.cursor()
        c.execute("""
            SELECT s.id,
                   s.name,
                   s.city,
                   s.area,
                   s.address,
                   s.octane_stock,
                   s.diesel_stock,
                   s.petrol_stock,
                   s.kerosene_stock,
                   s.octane_capacity,
                   s.diesel_capacity,
                   s.petrol_capacity,
                   s.kerosene_capacity,
                   s.octane_soft_reserved,
                   s.diesel_soft_reserved,
                   s.petrol_soft_reserved,
                   s.kerosene_soft_reserved,
                   s.is_active,
                   ss.id                    AS schedule_id,
                   ss.opening_time,
                   ss.closing_time,
                   ss.online_cutoff_time,
                   ss.pump_count,
                   ss.walkin_enabled,
                   ss.daily_cap,
                   ss.slot_duration_sedan,
                   ss.slot_duration_suv,
                   ss.slot_duration_motorcycle,
                   ss.slot_duration_motorcycle_rs,
                   ss.slot_duration_cng_auto,
                   ss.slot_duration_microbus,
                   ss.slot_duration_truck,
                   ss.slot_duration_bus
            FROM stations s
            JOIN station_schedule ss ON ss.station_id = s.id
            WHERE s.id=?
        """, (sid,))
        return c.fetchone()

    def get_all_stations(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT s.id,
                   s.name,
                   s.city,
                   s.area,
                   s.address,
                   s.octane_stock,
                   s.diesel_stock,
                   s.petrol_stock,
                   s.kerosene_stock,
                   s.octane_capacity,
                   s.diesel_capacity,
                   s.petrol_capacity,
                   s.kerosene_capacity,
                   s.is_active,
                   ss.id          AS schedule_id,
                   ss.opening_time,
                   ss.closing_time,
                   ss.walkin_enabled,
                   ss.pump_count
            FROM stations s
            JOIN station_schedule ss ON ss.station_id = s.id
            ORDER BY s.city, s.area
        """)
        return c.fetchall()

    def get_available_fuel(self, station_id, fuel_type):
        fuel_lower = fuel_type.lower()
        c = self.conn.cursor()
        c.execute(f"""
            SELECT {fuel_lower}_stock, {fuel_lower}_soft_reserved
            FROM stations WHERE id=?
        """, (station_id,))
        row = c.fetchone()
        if not row:
            return 0.0
        stock = row[0] or 0.0
        soft  = row[1] or 0.0

        c.execute("""
            SELECT COALESCE(SUM(requested_amount), 0)
            FROM bookings
            WHERE station_id=? AND fuel_type=?
            AND status IN ('scheduled','pending_approval','approved')
        """, (station_id, fuel_type))
        hard = c.fetchone()[0] or 0.0

        return max(0.0, stock - hard - soft)

    def is_fuel_open(self, station_id, fuel_type):
        fuel_lower = fuel_type.lower()
        c = self.conn.cursor()
        c.execute(f"""
            SELECT {fuel_lower}_capacity
            FROM stations WHERE id=?
        """, (station_id,))
        row = c.fetchone()
        if not row or not row[0]:
            return False
        cap       = row[0]
        available = self.get_available_fuel(station_id, fuel_type)
        return available > (cap * 0.10)

    def deduct_fuel(self, station_id, fuel_type, amount):
        fuel_lower = fuel_type.lower()
        c = self.conn.cursor()
        c.execute(f"""
            UPDATE stations
            SET {fuel_lower}_stock = MAX(0, {fuel_lower}_stock - ?)
            WHERE id=?
        """, (amount, station_id))
        self.conn.commit()

    def add_soft_reserve(self, station_id, fuel_type, amount):
        col = fuel_type.lower() + "_soft_reserved"
        c   = self.conn.cursor()
        c.execute(
            f"UPDATE stations SET {col}={col}+? WHERE id=?",
            (amount, station_id)
        )
        self.conn.commit()

    def remove_soft_reserve(self, station_id, fuel_type, amount):
        col = fuel_type.lower() + "_soft_reserved"
        c   = self.conn.cursor()
        c.execute(
            f"UPDATE stations SET {col}=MAX(0,{col}-?) WHERE id=?",
            (amount, station_id)
        )
        self.conn.commit()

    def log_resupply(self, station_id, fuel_type, quantity, user_id):
        fuel_lower = fuel_type.lower()
        cap_col    = fuel_lower + "_capacity"
        c = self.conn.cursor()
        c.execute(f"""
            UPDATE stations
            SET {fuel_lower}_stock = MIN({fuel_lower}_stock + ?, {cap_col})
            WHERE id=?
        """, (quantity, station_id))
        c.execute("""
            INSERT INTO resupply_log
            (station_id, fuel_type, quantity_added, logged_by)
            VALUES (?,?,?,?)
        """, (station_id, fuel_type, quantity, user_id))
        self.conn.commit()

    def toggle_walkin(self, station_id, enabled):
        c = self.conn.cursor()
        c.execute("""
            UPDATE station_schedule
            SET walkin_enabled=?
            WHERE station_id=?
        """, (1 if enabled else 0, station_id))
        self.conn.commit()

    def get_station_health(self, station_id):
        s = self.get_station_by_id(station_id)
        if not s:
            return "unknown"

        fuels   = ["octane","diesel","petrol","kerosene"]
        min_pct = 100.0
        for fl in fuels:
            try:
                cap = s[f"{fl}_capacity"]
                stk = s[f"{fl}_stock"]
                if cap and cap > 0:
                    min_pct = min(min_pct, (stk / cap) * 100)
            except Exception:
                pass

        c = self.conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM resupply_log
            WHERE station_id=?
            AND logged_at >= datetime('now','-7 days')
        """, (station_id,))
        recent_resupply = c.fetchone()[0]

        c.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE station_id=? AND status='no_show'
            AND slot_datetime >= datetime('now','-30 days')
        """, (station_id,))
        no_shows = c.fetchone()[0] or 0

        c.execute("""
            SELECT COUNT(*) FROM bookings
            WHERE station_id=?
            AND slot_datetime >= datetime('now','-30 days')
        """, (station_id,))
        total = max(c.fetchone()[0] or 1, 1)
        nsr   = (no_shows / total) * 100

        if min_pct < 15 or nsr > 25 or recent_resupply == 0:
            return "action"
        elif min_pct < 30 or nsr > 15:
            return "attention"
        return "good"

    def get_resupply_history(self, station_id, limit=10):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM resupply_log
            WHERE station_id=?
            ORDER BY logged_at DESC LIMIT ?
        """, (station_id, limit))
        return c.fetchall()

    def get_schedules_for_area(self, city, area):
        c = self.conn.cursor()
        c.execute("""
            SELECT ls.*, f.name AS feeder_name, f.area, f.city
            FROM load_shedding ls
            JOIN feeders f ON f.id = ls.feeder_id
            WHERE f.city=? AND f.area=?
            AND ls.start_datetime <= datetime('now','+7 days')
            ORDER BY ls.start_datetime
        """, (city, area))
        return c.fetchall()

    def check_48hr_change(self, city, area):
        c = self.conn.cursor()
        c.execute("""
            SELECT COUNT(*) FROM load_shedding ls
            JOIN feeders f ON f.id = ls.feeder_id
            WHERE f.city=? AND f.area=?
            AND ls.updated_at >= datetime('now','-48 hours')
            AND ls.updated_at != ls.created_at
        """, (city, area))
        return c.fetchone()[0] > 0

    def get_all_schedules_for_city(self, city):
        c = self.conn.cursor()
        c.execute("""
            SELECT ls.*, f.name AS feeder_name, f.area
            FROM load_shedding ls
            JOIN feeders f ON f.id = ls.feeder_id
            WHERE f.city=?
            ORDER BY ls.start_datetime DESC
        """, (city,))
        return c.fetchall()

    def get_feeders_for_city(self, city):
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM feeders WHERE city=? ORDER BY area", (city,)
        )
        return c.fetchall()

    def get_all_schedules_govt(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT ls.*, f.name AS feeder_name, f.area, f.city
            FROM load_shedding ls
            JOIN feeders f ON f.id = ls.feeder_id
            ORDER BY f.city, f.area, ls.start_datetime DESC
        """)
        return c.fetchall()

    def publish_schedule(self, feeder_id, start_dt, end_dt, note, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO load_shedding
            (feeder_id, start_datetime, end_datetime,
             internal_note, published_by)
            VALUES (?,?,?,?,?)
        """, (feeder_id, start_dt, end_dt, note, user_id))
        self.conn.commit()
        return c.lastrowid

    def update_schedule(self, schedule_id, start_dt, end_dt, note):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c   = self.conn.cursor()
        c.execute("""
            UPDATE load_shedding
            SET start_datetime=?, end_datetime=?,
                internal_note=?, updated_at=?
            WHERE id=?
        """, (start_dt, end_dt, note, now, schedule_id))
        self.conn.commit()

    def delete_schedule(self, schedule_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM load_shedding WHERE id=?", (schedule_id,))
        self.conn.commit()

    def delete_expired_schedules(self, city):
        c = self.conn.cursor()
        c.execute("""
            DELETE FROM load_shedding
            WHERE id IN (
                SELECT ls.id FROM load_shedding ls
                JOIN feeders f ON f.id = ls.feeder_id
                WHERE f.city=?
                AND ls.end_datetime < datetime('now')
            )
        """, (city,))
        self.conn.commit()
        return c.rowcount

    def token_exists(self, token):
        c = self.conn.cursor()
        c.execute("SELECT 1 FROM bookings WHERE token=?", (token,))
        if c.fetchone():
            return True
        c.execute("SELECT 1 FROM emergency_log WHERE token=?", (token,))
        return c.fetchone() is not None

    def get_booking_by_token(self, token):
        c = self.conn.cursor()
        c.execute("SELECT * FROM bookings WHERE token=?", (token,))
        return c.fetchone()

    def get_plate_booked_today(self, plate):
        c     = self.conn.cursor()
        today = date.today().strftime("%Y-%m-%d")
        c.execute("""
            SELECT * FROM bookings
            WHERE license_plate=?
            AND DATE(slot_datetime)=?
            AND status IN ('scheduled','pending_approval','approved')
        """, (plate, today))
        return c.fetchone()

    def get_booking_by_dl(self, dl):
        c = self.conn.cursor()
        c.execute("""
            SELECT b.*, s.name    AS station_name,
                        s.address AS station_address
            FROM bookings b
            JOIN stations s ON s.id = b.station_id
            WHERE b.driver_license=?
            AND b.status IN ('scheduled','pending_approval','approved')
            ORDER BY b.created_at DESC LIMIT 1
        """, (dl,))
        return c.fetchone()

    def get_booking_history_by_dl(self, dl, limit=20):
        c = self.conn.cursor()
        c.execute("""
            SELECT b.*, s.name AS station_name
            FROM bookings b
            JOIN stations s ON s.id = b.station_id
            WHERE b.driver_license=?
            ORDER BY b.created_at DESC LIMIT ?
        """, (dl, limit))
        return c.fetchall()

    def get_todays_bookings_for_station(self, station_id):
        c     = self.conn.cursor()
        today = date.today().strftime("%Y-%m-%d")
        c.execute("""
            SELECT * FROM bookings
            WHERE station_id=?
            AND DATE(slot_datetime)=?
            AND status IN ('scheduled','approved','pending_approval')
            ORDER BY slot_datetime
        """, (station_id, today))
        return c.fetchall()

    def get_pending_walkins(self, station_id):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM bookings
            WHERE station_id=? AND booking_type='walkin'
            AND status='pending_approval'
            ORDER BY created_at
        """, (station_id,))
        return c.fetchall()

    def create_booking(self, token, user_id, station_id, booking_type,
                       vehicle_type, fuel_type, plate, dl, name, email,
                       amount, price, slot_dt, purpose=None):
        est_cost   = amount * price
        month_year = datetime.now().strftime("%Y-%m")
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO bookings
            (token, user_id, station_id, booking_type, vehicle_type,
             fuel_type, license_plate, driver_license, full_name, email,
             requested_amount, price_per_litre, estimated_cost,
             status, slot_datetime, booking_purpose, month_year)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (token, user_id, station_id, booking_type, vehicle_type,
              fuel_type, plate, dl, name, email, amount, price,
              est_cost, "scheduled", slot_dt, purpose, month_year))
        self.conn.commit()
        return c.lastrowid

    def create_walkin_request(self, token, user_id, station_id,
                               vehicle_type, fuel_type, plate, dl,
                               name, email, amount, price):
        est_cost   = amount * price
        month_year = datetime.now().strftime("%Y-%m")
        now_str    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO bookings
            (token, user_id, station_id, booking_type, vehicle_type,
             fuel_type, license_plate, driver_license, full_name, email,
             requested_amount, price_per_litre, estimated_cost,
             status, slot_datetime, month_year)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'pending_approval',?,?)
        """, (token, user_id, station_id, "walkin", vehicle_type,
              fuel_type, plate, dl, name, email, amount, price,
              est_cost, now_str, month_year))
        self.conn.commit()
        return c.lastrowid

    def approve_walkin(self, booking_id, current_price):
        now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c        = self.conn.cursor()
        c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,))
        b        = c.fetchone()
        if not b:
            return False
        est_cost = b["requested_amount"] * current_price
        c.execute("""
            UPDATE bookings
            SET status='scheduled', slot_datetime=?,
                price_per_litre=?, estimated_cost=?
            WHERE id=?
        """, (now_str, current_price, est_cost, booking_id))
        self.conn.commit()
        return True

    def deny_walkin(self, booking_id, reason):
        c = self.conn.cursor()
        c.execute(
            "UPDATE bookings SET status='denied' WHERE id=?",
            (booking_id,)
        )
        self.conn.commit()

    def mark_serviced(self, token, actual_amount):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c       = self.conn.cursor()
        c.execute("SELECT * FROM bookings WHERE token=?", (token,))
        b       = c.fetchone()
        if not b:
            return None
        actual_cost = round(actual_amount * b["price_per_litre"], 2)
        c.execute("""
            UPDATE bookings
            SET status='serviced', actual_dispensed=?,
                actual_cost=?, serviced_at=?
            WHERE token=?
        """, (actual_amount, actual_cost, now_str, token))
        self.deduct_fuel(b["station_id"], b["fuel_type"], actual_amount)
        self.conn.commit()
        return b

    def cancel_booking(self, token):
        c = self.conn.cursor()
        c.execute(
            "UPDATE bookings SET status='cancelled' WHERE token=?",
            (token,)
        )
        self.conn.commit()

    def postpone_booking(self, token, new_slot):
        month_year = datetime.now().strftime("%Y-%m")
        c          = self.conn.cursor()
        c.execute("SELECT * FROM bookings WHERE token=?", (token,))
        b          = c.fetchone()
        if not b:
            return False
        old_slot = b["slot_datetime"]
        c.execute("""
            UPDATE bookings
            SET slot_datetime=?,
                postpone_count=postpone_count+1,
                pending_postpone=0
            WHERE token=?
        """, (new_slot, token))
        c.execute("""
            INSERT INTO postpone_log
            (booking_id, driver_license, original_slot,
             new_slot, month_year)
            VALUES (?,?,?,?,?)
        """, (b["id"], b["driver_license"], old_slot, new_slot, month_year))
        self.conn.commit()
        return True

    def get_postpone_count_this_month(self, dl):
        c  = self.conn.cursor()
        my = datetime.now().strftime("%Y-%m")
        c.execute("""
            SELECT COUNT(*) FROM postpone_log
            WHERE driver_license=? AND month_year=?
        """, (dl, my))
        return c.fetchone()[0]

    def set_pending_postpone(self, token, value):
        c = self.conn.cursor()
        c.execute(
            "UPDATE bookings SET pending_postpone=? WHERE token=?",
            (1 if value else 0, token)
        )
        self.conn.commit()

    def get_available_slots(self, station_id, target_date, vehicle_type):
        s = self.get_station_by_id(station_id)
        if not s:
            return []

        dur_map = {
            "Motorcycle (Personal)":   s["slot_duration_motorcycle"],
            "Motorcycle (Ride Share)": s["slot_duration_motorcycle_rs"],
            "CNG Auto":                s["slot_duration_cng_auto"],
            "Sedan":                   s["slot_duration_sedan"],
            "SUV":                     s["slot_duration_suv"],
            "Microbus":                s["slot_duration_microbus"],
            "Truck":                   s["slot_duration_truck"],
            "Bus":                     s["slot_duration_bus"],
        }
        duration   = dur_map.get(vehicle_type, 6)
        pump_count = s["pump_count"]

        open_h, open_m = map(int, s["opening_time"].split(":"))
        cut_h,  cut_m  = map(int, s["online_cutoff_time"].split(":"))

        opening = datetime.combine(
            target_date,
            datetime.min.time().replace(hour=open_h, minute=open_m)
        )
        cutoff = datetime.combine(
            target_date,
            datetime.min.time().replace(hour=cut_h, minute=cut_m)
        )

        now = datetime.now()
        if target_date == date.today():
            start = max(opening, now + timedelta(minutes=30))
        else:
            start = opening

        c = self.conn.cursor()
        c.execute("""
            SELECT slot_datetime FROM bookings
            WHERE station_id=?
            AND DATE(slot_datetime)=?
            AND status IN ('scheduled','pending_approval','approved')
        """, (station_id, target_date.strftime("%Y-%m-%d")))
        taken_slots = [r[0] for r in c.fetchall()]

        available = []
        current   = start
        while current <= cutoff:
            slot_str  = current.strftime("%Y-%m-%d %H:%M:%S")
            taken_cnt = sum(1 for t in taken_slots if t == slot_str)
            if taken_cnt < pump_count:
                available.append(current)
            current += timedelta(minutes=duration)

        return available

    def get_station_analytics(self, station_id, period="week"):
        intervals = {"week":"-7 days","month":"-30 days","year":"-365 days"}
        iv = intervals.get(period, "-7 days")
        c  = self.conn.cursor()

        c.execute("""
            SELECT DATE(slot_datetime) AS day,
                   COUNT(*)            AS total,
                   COALESCE(SUM(actual_dispensed),0) AS dispensed,
                   COALESCE(SUM(actual_cost),0)      AS revenue
            FROM bookings
            WHERE station_id=? AND status='serviced'
            AND slot_datetime >= datetime('now',?)
            GROUP BY DATE(slot_datetime)
            ORDER BY day
        """, (station_id, iv))
        daily = c.fetchall()

        c.execute("""
            SELECT vehicle_type, COUNT(*) AS cnt
            FROM bookings
            WHERE station_id=? AND status='serviced'
            AND slot_datetime >= datetime('now',?)
            GROUP BY vehicle_type
        """, (station_id, iv))
        by_vehicle = c.fetchall()

        c.execute("""
            SELECT fuel_type,
                   COALESCE(SUM(actual_dispensed),0) AS dispensed
            FROM bookings
            WHERE station_id=? AND status='serviced'
            AND slot_datetime >= datetime('now',?)
            GROUP BY fuel_type
        """, (station_id, iv))
        by_fuel = c.fetchall()

        return {
            "daily":      daily,
            "by_vehicle": by_vehicle,
            "by_fuel":    by_fuel,
        }

    def get_national_analytics(self, period="week"):
        intervals = {"week":"-7 days","month":"-30 days","year":"-365 days"}
        iv = intervals.get(period, "-7 days")
        c  = self.conn.cursor()

        c.execute("""
            SELECT DATE(slot_datetime) AS day,
                   COUNT(*)            AS total,
                   COALESCE(SUM(actual_dispensed),0) AS dispensed,
                   COALESCE(SUM(actual_cost),0)      AS revenue
            FROM bookings
            WHERE status='serviced'
            AND slot_datetime >= datetime('now',?)
            GROUP BY DATE(slot_datetime)
            ORDER BY day
        """, (iv,))
        daily = c.fetchall()

        c.execute("""
            SELECT vehicle_type, COUNT(*) AS cnt
            FROM bookings
            WHERE status='serviced'
            AND slot_datetime >= datetime('now',?)
            GROUP BY vehicle_type
        """, (iv,))
        by_vehicle = c.fetchall()

        c.execute("""
            SELECT s.name, s.city,
                   COUNT(*)                          AS cnt,
                   COALESCE(SUM(b.actual_dispensed),0) AS dispensed
            FROM bookings b
            JOIN stations s ON s.id = b.station_id
            WHERE b.status='serviced'
            AND b.slot_datetime >= datetime('now',?)
            GROUP BY b.station_id
            ORDER BY cnt DESC
        """, (iv,))
        by_station = c.fetchall()

        return {
            "daily":      daily,
            "by_vehicle": by_vehicle,
            "by_station": by_station,
        }

    def get_electricity_analytics(self, city=None, period="week"):
        intervals = {"week":"-7 days","month":"-30 days","year":"-365 days"}
        iv     = intervals.get(period, "-7 days")
        c      = self.conn.cursor()
        params = [iv]
        query  = """
            SELECT f.area, f.city, f.name AS feeder_name,
                   COUNT(*) AS events,
                   ROUND(SUM(
                       (julianday(ls.end_datetime) -
                        julianday(ls.start_datetime)) * 24
                   ), 2) AS total_hours
            FROM load_shedding ls
            JOIN feeders f ON f.id = ls.feeder_id
            WHERE ls.start_datetime >= datetime('now',?)
        """
        if city:
            query  += " AND f.city=?"
            params.append(city)
        query += " GROUP BY f.area ORDER BY total_hours DESC"
        c.execute(query, params)
        return c.fetchall()

    def validate_booking_request(self, station_id, vehicle_type,
                                  fuel_type, plate, dl, amount):
        errors = []
        suspension = self.get_active_suspension(dl)
        if suspension:
            try:
                from utils import format_suspension_message
                errors.append(format_suspension_message(suspension))
            except Exception:
                until = suspension["suspended_until"]
                errors.append(
                    f"Your booking access is restricted until {until}. "
                    f"Reason: {suspension['reason']}"
                )
            return errors

        existing = self.get_plate_booked_today(plate)
        if existing:
            errors.append(
                "This vehicle has already been booked for fuel today. "
                "Each vehicle may only be booked once per calendar day."
            )
            return errors

        daily_limit = self.get_daily_limit(vehicle_type, fuel_type)
        if amount > daily_limit:
            errors.append(
                f"Requested amount of {int(amount)}L exceeds the daily "
                f"limit of {int(daily_limit)}L for "
                f"{vehicle_type} + {fuel_type}."
            )

        if not self.is_fuel_open(station_id, fuel_type):
            errors.append(
                f"Appointments currently closed for {fuel_type} "
                f"at this station."
            )
        else:
            available = self.get_available_fuel(station_id, fuel_type)
            if amount > available:
                errors.append(
                    f"Appointments currently closed for {fuel_type} "
                    f"at this station."
                )

        return errors

    def get_active_suspension(self, dl):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM suspensions
            WHERE driver_license=? AND is_active=1
            AND suspended_until > datetime('now')
            ORDER BY suspended_until DESC LIMIT 1
        """, (dl,))
        return c.fetchone()

    def apply_suspension(self, dl, suspension_type, reason, hours):
        now   = datetime.now()
        until = now + timedelta(hours=hours)
        c     = self.conn.cursor()
        c.execute("""
            INSERT INTO suspensions
            (driver_license, suspension_type, reason, suspended_until)
            VALUES (?,?,?,?)
        """, (dl, suspension_type, reason,
              until.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()

    def lift_suspension(self, suspension_id, govt_id, note):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c       = self.conn.cursor()
        c.execute("""
            UPDATE suspensions
            SET is_active=0, lifted_by=?, lift_note=?, lifted_at=?
            WHERE id=?
        """, (govt_id, note, now_str, suspension_id))
        self.conn.commit()

    def get_all_active_suspensions(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT s.*, u.full_name, u.email
            FROM suspensions s
            JOIN users u ON u.driver_license = s.driver_license
            WHERE s.is_active=1
            AND s.suspended_until > datetime('now')
            ORDER BY s.suspended_until
        """)
        return c.fetchall()


    def join_waitlist(self, user_id, station_id, fuel_type,
                      vehicle_type, plate, amount,
                      waitlist_type="advance",
                      original_booking_id=None, days_ahead=0):
        now = datetime.now()
        if waitlist_type == "advance":
            exp = datetime.combine(
                date.today() + timedelta(days=days_ahead),
                datetime.max.time()
            ).replace(microsecond=0)
        else:
            exp = now + timedelta(days=3)

        c = self.conn.cursor()

        c.execute("""
            SELECT id FROM waitlist
            WHERE user_id=? AND station_id=? AND fuel_type=?
            AND license_plate=? AND status='waiting'
            AND expires_at > datetime('now')
        """, (user_id, station_id, fuel_type, plate))
        if c.fetchone():
            return None

        c.execute("""
            INSERT INTO waitlist
            (user_id, station_id, fuel_type, vehicle_type,
             license_plate, requested_amount, waitlist_type,
             original_booking_id, expires_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (user_id, station_id, fuel_type, vehicle_type, plate,
              amount, waitlist_type, original_booking_id,
              exp.strftime("%Y-%m-%d %H:%M:%S")))
        self.conn.commit()
        return c.lastrowid

    def get_waitlist_for_user(self, user_id):
        c = self.conn.cursor()
        c.execute("""
            SELECT w.*, s.name AS station_name
            FROM waitlist w
            JOIN stations s ON s.id = w.station_id
            WHERE w.user_id=?
            AND w.status IN ('waiting','notified')
            AND w.expires_at > datetime('now')
        """, (user_id,))
        return c.fetchall()

    def get_waitlist_position(self, waitlist_id):
        c = self.conn.cursor()
        c.execute("SELECT * FROM waitlist WHERE id=?", (waitlist_id,))
        e = c.fetchone()
        if not e:
            return 0
        c.execute("""
            SELECT COUNT(*) FROM waitlist
            WHERE station_id=? AND fuel_type=? AND waitlist_type=?
            AND status='waiting'
            AND joined_at < ?
        """, (e["station_id"], e["fuel_type"],
              e["waitlist_type"], e["joined_at"]))
        return c.fetchone()[0] + 1

    def cancel_waitlist(self, waitlist_id):
        c = self.conn.cursor()
        c.execute(
            "UPDATE waitlist SET status='cancelled' WHERE id=?",
            (waitlist_id,)
        )
        self.conn.commit()

    def get_emergency_booking_by_dl(self, dl):
        c = self.conn.cursor()
        c.execute("""
            SELECT el.*, s.name    AS station_name,
                         s.address AS station_address
            FROM emergency_log el
            JOIN stations s ON s.id = el.station_id
            WHERE el.driver_license=?
            AND el.status='scheduled'
            ORDER BY el.created_at DESC LIMIT 1
        """, (dl,))
        return c.fetchone()

    def get_active_waitlist_offer(self, user_id):
        c = self.conn.cursor()
        c.execute("""
            SELECT w.*, s.name    AS station_name,
                         s.address AS station_address
            FROM waitlist w
            JOIN stations s ON s.id = w.station_id
            WHERE w.user_id=?
            AND w.status='notified'
            AND w.offer_expires_at > datetime('now')
            ORDER BY w.offer_expires_at ASC LIMIT 1
        """, (user_id,))
        return c.fetchone()

    def get_daily_limit(self, vehicle_type, fuel_type):
        c = self.conn.cursor()
        c.execute("""
            SELECT max_litres FROM daily_limit_rules
            WHERE vehicle_type=? AND fuel_type=?
        """, (vehicle_type, fuel_type))
        row = c.fetchone()
        return row[0] if row else 999.0

    def get_all_daily_limits(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM daily_limit_rules
            ORDER BY vehicle_type, fuel_type
        """)
        return c.fetchall()

    def set_daily_limit(self, vehicle_type, fuel_type, max_litres, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO daily_limit_rules
            (vehicle_type, fuel_type, max_litres, set_by)
            VALUES (?,?,?,?)
            ON CONFLICT(vehicle_type, fuel_type)
            DO UPDATE SET max_litres=?, set_by=?,
            updated_at=CURRENT_TIMESTAMP
        """, (vehicle_type, fuel_type, max_litres, user_id,
              max_litres, user_id))
        self.conn.commit()

    def get_fuel_price(self, fuel_type):
        c = self.conn.cursor()
        c.execute("""
            SELECT price_per_litre FROM fuel_prices
            WHERE fuel_type=?
        """, (fuel_type,))
        row = c.fetchone()
        return row[0] if row else 0.0

    def get_all_fuel_prices(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM fuel_prices ORDER BY fuel_type")
        return c.fetchall()

    def set_fuel_price(self, fuel_type, price, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO fuel_prices (fuel_type, price_per_litre, set_by)
            VALUES (?,?,?)
            ON CONFLICT(fuel_type)
            DO UPDATE SET price_per_litre=?, set_by=?,
            updated_at=CURRENT_TIMESTAMP
        """, (fuel_type, price, user_id, price, user_id))
        self.conn.commit()


    def check_emergency_vehicle(self, reg_number):
        c = self.conn.cursor()
        c.execute("""
            SELECT sv.*, sve.is_enabled
            FROM special_vehicles sv
            JOIN special_vehicle_eligibility sve
            ON sve.vehicle_category = sv.vehicle_category
            WHERE sv.registration_number=? AND sv.is_active=1
        """, (reg_number,))
        return c.fetchone()

    def get_all_special_vehicles(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT sv.*, sve.is_enabled
            FROM special_vehicles sv
            JOIN special_vehicle_eligibility sve
            ON sve.vehicle_category = sv.vehicle_category
            ORDER BY sv.vehicle_category
        """)
        return c.fetchall()

    def get_eligibility_settings(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM special_vehicle_eligibility
            ORDER BY vehicle_category
        """)
        return c.fetchall()

    def set_eligibility(self, category, enabled, user_id):
        c = self.conn.cursor()
        c.execute("""
            UPDATE special_vehicle_eligibility
            SET is_enabled=?, set_by=?, updated_at=CURRENT_TIMESTAMP
            WHERE vehicle_category=?
        """, (1 if enabled else 0, user_id, category))
        self.conn.commit()

    def register_special_vehicle(self, reg, category, org, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO special_vehicles
            (registration_number, vehicle_category, organisation,
             is_active, registered_by)
            VALUES (?,?,?,1,?)
        """, (reg, category, org, user_id))
        self.conn.commit()

    def deactivate_special_vehicle(self, vehicle_id):
        c = self.conn.cursor()
        c.execute(
            "UPDATE special_vehicles SET is_active=0 WHERE id=?",
            (vehicle_id,)
        )
        self.conn.commit()

    def create_emergency_booking(self, token, reg, category, org,
                                  station_id, dl, fuel_type, amount,
                                  price, eta_min, eta_dt):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO emergency_log
            (token, registration_number, vehicle_category, organisation,
             station_id, driver_license, fuel_type, requested_amount,
             price_per_litre, eta_minutes, eta_datetime)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (token, reg, category, org, station_id, dl,
              fuel_type, amount, price, eta_min, eta_dt))
        self.conn.commit()

    def get_emergency_by_token(self, token):
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM emergency_log WHERE token=?", (token,)
        )
        return c.fetchone()

    def service_emergency(self, token, actual_amount):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c       = self.conn.cursor()
        c.execute(
            "SELECT * FROM emergency_log WHERE token=?", (token,)
        )
        b = c.fetchone()
        if not b:
            return None
        actual_cost = round(actual_amount * b["price_per_litre"], 2)
        c.execute("""
            UPDATE emergency_log
            SET status='serviced', actual_dispensed=?,
                serviced_at=?
            WHERE token=?
        """, (actual_amount, now_str, token))
        self.deduct_fuel(b["station_id"], b["fuel_type"], actual_amount)
        self.conn.commit()
        return b

    def get_todays_emergency_for_station(self, station_id):
        c     = self.conn.cursor()
        today = date.today().strftime("%Y-%m-%d")
        c.execute("""
            SELECT * FROM emergency_log
            WHERE station_id=?
            AND DATE(created_at)=?
            AND status IN ('scheduled','serviced')
            ORDER BY eta_datetime
        """, (station_id, today))
        return c.fetchall()

    def get_emergency_history(self, limit=20):
        c = self.conn.cursor()
        c.execute("""
            SELECT el.*, s.name AS station_name
            FROM emergency_log el
            JOIN stations s ON s.id = el.station_id
            ORDER BY el.created_at DESC LIMIT ?
        """, (limit,))
        return c.fetchall()


    def get_active_announcements(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM announcements
            WHERE is_active=1
            AND expires_at > datetime('now')
            ORDER BY published_at DESC
        """)
        return c.fetchall()

    def get_all_announcements(self):
        c = self.conn.cursor()
        c.execute(
            "SELECT * FROM announcements ORDER BY published_at DESC"
        )
        return c.fetchall()

    def publish_announcement(self, title, message, expires_at, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO announcements
            (title, message, published_by, expires_at)
            VALUES (?,?,?,?)
        """, (title, message, user_id, expires_at))
        self.conn.commit()

    def deactivate_announcement(self, ann_id):
        c = self.conn.cursor()
        c.execute(
            "UPDATE announcements SET is_active=0 WHERE id=?", (ann_id,)
        )
        self.conn.commit()

    def log_audit(self, user_id, action, details, log_type="fuel"):
        u    = self.get_user_by_id(user_id)
        name = u["full_name"] if u else "System"
        role = u["role"]      if u else "system"
        c    = self.conn.cursor()
        c.execute("""
            INSERT INTO audit_log
            (user_id, user_name, role, action, details, log_type)
            VALUES (?,?,?,?,?,?)
        """, (user_id, name, role, action, details, log_type))
        self.conn.commit()

    def get_audit_log(self, log_type=None, limit=100):
        c = self.conn.cursor()
        if log_type:
            c.execute("""
                SELECT * FROM audit_log WHERE log_type=?
                ORDER BY timestamp DESC LIMIT ?
            """, (log_type, limit))
        else:
            c.execute("""
                SELECT * FROM audit_log
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        return c.fetchall()


    def search_by_plate(self, plate):
        c = self.conn.cursor()
        c.execute("""
            SELECT b.*, s.name AS station_name
            FROM bookings b
            JOIN stations s ON s.id = b.station_id
            WHERE b.license_plate=?
            ORDER BY b.created_at DESC
        """, (plate,))
        return c.fetchall()

    def search_by_dl(self, dl):
        c = self.conn.cursor()
        c.execute("""
            SELECT b.*, s.name AS station_name
            FROM bookings b
            JOIN stations s ON s.id = b.station_id
            WHERE b.driver_license=?
            ORDER BY b.created_at DESC
        """, (dl,))
        return c.fetchall()


    def add_restriction(self, rtype, value, max_bookings,
                        period_hours, user_id):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO license_restrictions
            (restriction_type, value, max_bookings,
             period_hours, set_by)
            VALUES (?,?,?,?,?)
        """, (rtype, value, max_bookings, period_hours, user_id))
        self.conn.commit()

    def get_all_restrictions(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM license_restrictions
            ORDER BY created_at DESC
        """)
        return c.fetchall()

    def delete_restriction(self, restriction_id):
        c = self.conn.cursor()
        c.execute(
            "DELETE FROM license_restrictions WHERE id=?",
            (restriction_id,)
        )
        self.conn.commit()

    def cleanup_expired(self):
        self._mark_no_shows()
        self._expire_waitlist_entries()
        self._reset_stale_6month_counters()
        
    def _mark_no_shows(self):
        c     = self.conn.cursor()
        today = date.today().strftime("%Y-%m-%d")
        c.execute("""
            SELECT * FROM bookings
            WHERE status='scheduled'
            AND DATE(slot_datetime) < ?
            AND pending_postpone=0
        """, (today,))
        overdue = c.fetchall()

        for b in overdue:
            c.execute(
                "UPDATE bookings SET status='no_show' WHERE id=?",
                (b["id"],)
            )
            c.execute("""
                UPDATE users
                SET no_show_count_lifetime = no_show_count_lifetime + 1,
                    no_show_count_6months  = no_show_count_6months  + 1
                WHERE driver_license=?
            """, (b["driver_license"],))

            c.execute("""
                SELECT no_show_count_6months, no_show_count_lifetime
                FROM users WHERE driver_license=?
            """, (b["driver_license"],))
            row = c.fetchone()
            if not row:
                continue
            count_6m, count_life = row[0], row[1]

            existing = self.get_active_suspension(b["driver_license"])
            if not existing:
                if count_6m == 2:
                    self.apply_suspension(
                        b["driver_license"], "no_show",
                        "You missed 2 appointments without cancelling.",
                        168
                    )
                elif count_life == 3:
                    self.apply_suspension(
                        b["driver_license"], "no_show",
                        "You have a history of missing appointments.",
                        336
                    )
                elif count_life == 4:
                    self.apply_suspension(
                        b["driver_license"], "no_show",
                        "Repeated missed appointments.",
                        720
                    )
                elif count_life >= 5:
                    c.execute("""
                        UPDATE users SET is_flagged=1
                        WHERE driver_license=?
                    """, (b["driver_license"],))

        self.conn.commit()

    def _expire_waitlist_entries(self):
        c = self.conn.cursor()
        c.execute("""
            UPDATE waitlist SET status='expired'
            WHERE status='waiting'
            AND expires_at < datetime('now')
        """)
        try:
            self.conn.commit()
        except Exception:
            pass

    def _reset_stale_6month_counters(self):
        c = self.conn.cursor()
        c.execute("""
            UPDATE users
            SET no_show_count_6months = 0
            WHERE no_show_count_6months > 0
            AND id IN (
                SELECT DISTINCT u.id FROM users u
                WHERE (
                    SELECT MAX(b.slot_datetime)
                    FROM bookings b
                    WHERE b.driver_license = u.driver_license
                    AND b.status = 'no_show'
                ) < datetime('now', '-6 months')
                OR (
                    SELECT COUNT(*) FROM bookings b
                    WHERE b.driver_license = u.driver_license
                    AND b.status = 'no_show'
                ) = 0
            )
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()
