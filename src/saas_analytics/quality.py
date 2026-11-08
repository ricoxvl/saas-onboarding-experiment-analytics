"""Event-level QA checks; validate data BEFORE drawing experiment conclusions."""
from collections import Counter, defaultdict
from datetime import datetime

BINARY_FLAGS = (
    "workspace_created", "integration_connected", "teammate_invited",
    "onboarding_error_d7", "support_ticket_d7", "activated_d7", "returned_d28",
)
EVENT_FLAGS = {
    "workspace_created": "workspace_created",
    "integration_connected": "integration_connected",
    "teammate_invited": "teammate_invited",
    "onboarding_error": "onboarding_error_d7",
    "support_ticket": "support_ticket_d7",
    "returned_d28": "returned_d28",
}
ALLOWED_EVENTS = set(EVENT_FLAGS) | {"signup"}


def audit_database(conn):
    """Return a machine-readable, deterministic audit with per-check error counts."""
    issues = Counter({
        "duplicate_user_ids": 0,
        "invalid_assignment_or_segment": 0,
        "invalid_binary_fields": 0,
        "invalid_signup_metadata": 0,
        "broken_activation_logic": 0,
        "orphan_or_unknown_events": 0,
        "duplicate_or_missing_events": 0,
        "event_flag_mismatches": 0,
        "invalid_event_timing": 0,
    })
    users = [dict(r) for r in conn.execute("SELECT * FROM users ORDER BY user_id")]
    events = [dict(r) for r in conn.execute("SELECT * FROM events ORDER BY event_id")]
    user_by_id = {}
    for u in users:
        uid = u["user_id"]
        if uid in user_by_id:
            issues["duplicate_user_ids"] += 1
        user_by_id[uid] = u
        if u["variant"] not in {"control", "treatment"} or u["segment"] not in {"solo", "team"}:
            issues["invalid_assignment_or_segment"] += 1
        if any(u[k] not in (0, 1) for k in BINARY_FLAGS):
            issues["invalid_binary_fields"] += 1
        try:
            signup = datetime.fromisoformat(u["signup_at"])
            if signup.tzinfo is None or u["signup_month"] != signup.strftime("%Y-%m"):
                issues["invalid_signup_metadata"] += 1
        except (TypeError, ValueError):
            issues["invalid_signup_metadata"] += 1
        if (
            u["integration_connected"] > u["workspace_created"]
            or u["teammate_invited"] > u["integration_connected"]
            or u["activated_d7"] != int(bool(u["workspace_created"] and u["integration_connected"]))
        ):
            issues["broken_activation_logic"] += 1

    counts = defaultdict(Counter)
    for e in events:
        uid, name = e["user_id"], e["event_name"]
        if uid not in user_by_id or name not in ALLOWED_EVENTS:
            issues["orphan_or_unknown_events"] += 1
            continue
        counts[uid][name] += 1
        try:
            observed = datetime.fromisoformat(e["event_at"])
            signup = datetime.fromisoformat(user_by_id[uid]["signup_at"])
            diff_days = (observed - signup).total_seconds() / 86400
            expected = (
                abs(diff_days - 28) < 1e-6 if name == "returned_d28"
                else abs(diff_days) < 1e-6 if name == "signup"
                else 0 <= diff_days <= 7
            )
            if not expected or observed.tzinfo is None:
                issues["invalid_event_timing"] += 1
        except (TypeError, ValueError):
            issues["invalid_event_timing"] += 1

    for uid, u in user_by_id.items():
        observed = counts[uid]
        if observed["signup"] != 1 or any(n > 1 for n in observed.values()):
            issues["duplicate_or_missing_events"] += 1
        if any(observed[event] != u[flag] for event, flag in EVENT_FLAGS.items()):
            issues["event_flag_mismatches"] += 1

    return {
        "passed": not any(issues.values()),
        "users_checked": len(users),
        "events_checked": len(events),
        "issue_counts": dict(issues),
    }
