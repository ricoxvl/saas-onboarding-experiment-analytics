-- SQL reference queries for the synthetic SaaS SQLite dataset.
-- Primary analysis is intention-to-treat: assigned users remain in their original group.

-- Signup-to-activation funnel, by assigned variant.
SELECT variant,
       COUNT(*) AS signups,
       SUM(workspace_created) AS created_workspace,
       SUM(integration_connected) AS connected_integration,
       SUM(activated_d7) AS activated_within_7_days,
       ROUND(100.0 * SUM(activated_d7) / COUNT(*), 2) AS activation_rate_pct
FROM users
GROUP BY variant;

-- Monthly signup cohorts; day-28 retention denominator is all users in cohort.
SELECT signup_month, variant, COUNT(*) AS users,
       SUM(returned_d28) AS day_28_returning,
       ROUND(100.0 * SUM(returned_d28) / COUNT(*), 2) AS day_28_retention_pct
FROM users
GROUP BY signup_month, variant
ORDER BY signup_month, variant;

-- Negative-outcome guardrail incidence, by assigned arm.
SELECT variant,
       COUNT(*) AS assigned_users,
       SUM(onboarding_error_d7) AS users_with_onboarding_error,
       ROUND(100.0 * SUM(onboarding_error_d7) / COUNT(*), 2) AS error_rate_pct,
       SUM(support_ticket_d7) AS users_with_support_ticket,
       ROUND(100.0 * SUM(support_ticket_d7) / COUNT(*), 2) AS support_rate_pct
FROM users
GROUP BY variant
ORDER BY variant;

-- Team/solo retention effects are exploratory: calculate adjusted q-values in Python.
SELECT segment, variant, COUNT(*) AS assigned_users,
       SUM(returned_d28) AS day_28_returning,
       ROUND(100.0 * SUM(returned_d28) / COUNT(*), 2) AS retention_pct
FROM users
GROUP BY segment, variant
ORDER BY segment, variant;

-- Event-level audit for potential multiple/duplicate events (normally none).
SELECT user_id, event_name, COUNT(*) AS n
FROM events
GROUP BY user_id, event_name
HAVING COUNT(*) > 1;
