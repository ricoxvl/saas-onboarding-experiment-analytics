# Data dictionary

All records are **synthetic**. UTC timestamps use ISO-8601 strings.

## users (one row per randomized user)
| Column | Meaning |
| --- | --- |
| user_id | Synthetic stable key |
| signup_at | Synthetic signup event time (UTC) |
| signup_month | YYYY-MM cohort |
| variant | Assigned group: control or treatment |
| segment | Fictional solo or team signup segment |
| workspace_created | 1 if workspace created within D7 |
| integration_connected | 1 if integration connected within D7 |
| teammate_invited | 1 if teammate invited by day 2 |
| onboarding_error_d7 | 1 if an onboarding-error event occurred by day 7; negative-outcome guardrail |
| support_ticket_d7 | 1 if a support ticket event occurred by day 7; negative-outcome guardrail |
| activated_d7 | 1 if both workspace and integration completed within D7 |
| returned_d28 | 1 if active on the 28th day after signup |

## events (one row per generated event)
| Column | Meaning |
| --- | --- |
| event_id | Event primary key |
| user_id | References users.user_id |
| event_at | UTC event timestamp |
| event_name | signup, workspace_created, integration_connected, teammate_invited, onboarding_error, support_ticket, or returned_d28 |

The event generator uses fixed offsets for post-signup events, enabling simple reproducible testing. This is not a model of continuous product use. All event flags are reconciled to their corresponding event rows in the data-quality audit.
