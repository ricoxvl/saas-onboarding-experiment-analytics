# Project brief

## Context
A fictional B2B SaaS business sees user drop-off between signup, workspace creation, integration connection, and return usage.

## Decision
Should the product team replace a standard onboarding experience with a guided onboarding flow?

## Hypothesis
Guided onboarding may increase day-28 return activity. This is a hypothetical experiment; the pipeline uses **synthetically simulated behavior**, not observed customer outcomes.

## Experimental plan
- **Unit of randomization and analysis:** unique new user
- **Arms:** standard flow (control) vs guided flow (treatment), 50/50 random assignment
- **Primary metric:** user returned on signup day +28 (binary); denominator = all randomized users
- **Supporting metric:** activation within seven days, defined as workspace creation AND integration connection within seven days
- **Exploratory cuts:** solo vs team users and signup month, clearly marked exploratory
- **SRM check:** chi-square test against 50/50, flag when p < 0.001
- **Effect measure:** absolute difference in binary rates (treatment - control), with 95% CI and two-sided z-test
- **Decision principles:** assess business significance and interval uncertainty alongside p-value; review onboarding guardrails and segment heterogeneity before any actual rollout decision.

## Simulation assumptions
- 4,000 default users; seeded pseudo-random assignment and outcomes.
- Users sign up during a 90-day window starting January 1, 2026.
- Fictional treatment users are configured with moderately higher completion and return probabilities.
- Return probabilities depend on assignment, activation, and team/solo segment; such a model embeds assumptions, **not** empirical causality.
- Outcomes are generated fully matured. A live trial would need observation windows, censoring checks, instrumentation QA, privacy safeguards, and a pre-registered stopping rule.

## Future deliverables
Dashboard, segment uncertainty, power/MDE sensitivity, and a final decision memo using transparent simulated results.
