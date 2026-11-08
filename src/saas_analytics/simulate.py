"""Generate a reproducible, synthetic, randomized SaaS onboarding dataset."""
import argparse
import csv
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "generated"
BASE_DATE = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)

USER_FIELDS = [
    "user_id", "signup_at", "signup_month", "variant", "segment",
    "workspace_created", "integration_connected", "teammate_invited",
    "activated_d7", "returned_d28",
]
EVENT_FIELDS = ["event_id", "user_id", "event_at", "event_name"]


def generate(users=4000, seed=42, output_dir=DATA):
    if users < 2:
        raise ValueError("users must be at least 2")
    rng = random.Random(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    user_rows, event_rows = [], []
    event_id = 0

    def event(user_id, timestamp, name):
        nonlocal event_id
        event_id += 1
        event_rows.append({
            "event_id": event_id,
            "user_id": user_id,
            "event_at": timestamp.isoformat(),
            "event_name": name,
        })

    for i in range(users):
        uid = f"u{i + 1:06d}"
        variant = "treatment" if rng.random() < 0.5 else "control"
        segment = "team" if rng.random() < 0.45 else "solo"
        signup = BASE_DATE + timedelta(days=rng.randint(0, 89), hours=rng.randint(0, 11))
        # Explicitly fictional probabilities; treatment affects completion and return.
        workspace_probability = 0.84 if variant == "treatment" else 0.78
        integration_probability = 0.77 if variant == "treatment" else 0.70
        workspace = rng.random() < workspace_probability
        integration = workspace and rng.random() < integration_probability
        invited = bool(integration and segment == "team" and rng.random() < 0.55)
        activated = bool(workspace and integration)
        return_probability = (0.54 if variant == "treatment" else 0.49)
        return_probability += 0.09 if activated else -0.09
        return_probability += 0.03 if segment == "team" else 0
        returned = rng.random() < return_probability
        event(uid, signup, "signup")
        if workspace:
            event(uid, signup + timedelta(hours=2), "workspace_created")
        if integration:
            event(uid, signup + timedelta(hours=9), "integration_connected")
        if invited:
            event(uid, signup + timedelta(days=2), "teammate_invited")
        if returned:
            event(uid, signup + timedelta(days=28), "returned_d28")
        user_rows.append({
            "user_id": uid,
            "signup_at": signup.isoformat(),
            "signup_month": signup.strftime("%Y-%m"),
            "variant": variant,
            "segment": segment,
            "workspace_created": int(workspace),
            "integration_connected": int(integration),
            "teammate_invited": int(invited),
            "activated_d7": int(activated),
            "returned_d28": int(returned),
        })

    for filename, fields, rows in [
        ("users.csv", USER_FIELDS, user_rows),
        ("events.csv", EVENT_FIELDS, event_rows),
    ]:
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    db_path = output_dir / "saas.db"
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE users (
            user_id TEXT PRIMARY KEY, signup_at TEXT, signup_month TEXT,
            variant TEXT, segment TEXT, workspace_created INTEGER,
            integration_connected INTEGER, teammate_invited INTEGER,
            activated_d7 INTEGER, returned_d28 INTEGER
        )""")
        conn.execute("""CREATE TABLE events (
            event_id INTEGER PRIMARY KEY, user_id TEXT, event_at TEXT,
            event_name TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id)
        )""")
        conn.executemany(
            "INSERT INTO users VALUES (" + ",".join("?" for _ in USER_FIELDS) + ")",
            [[r[k] for k in USER_FIELDS] for r in user_rows],
        )
        conn.executemany(
            "INSERT INTO events VALUES (" + ",".join("?" for _ in EVENT_FIELDS) + ")",
            [[r[k] for k in EVENT_FIELDS] for r in event_rows],
        )
        conn.execute("CREATE INDEX events_user_idx ON events(user_id)")
    return {"users": len(user_rows), "events": len(event_rows), "database": str(db_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--users", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=DATA)
    args = parser.parse_args()
    print(generate(args.users, args.seed, args.output_dir))


if __name__ == "__main__":
    main()
