# Optional payments — Stripe

Only add payments when requested by the owner. Availability of credentials is not
authorization to create live charges, subscriptions, refunds or account changes.

## Credentials and access

The administrator stores STRIPE_SECRET_KEY in /etc/lab/stripe.env, root:root 0600,
outside Git. Experiment agents running as lab cannot read this file. It is not
automatically loaded into apps or included by labctl secrets-list/secrets-grant.
Ask the platform administrator to provision credentials for the selected app; do
not change permissions to expose the shared file. On a fresh machine, the owner
enters their own key securely here. Never put values in settings.txt or chat.

Prefer an app-specific restricted key with permissions matched to the integration.
For the existing grant mechanism, the administrator can securely merge that key
into /etc/lab/secrets.env under a unique name such as STRIPE_EXAMPLE_TEST_KEY, then
grant that name to NAME using labctl secrets-grant and restart NAME. The app reads
that explicit environment name. Never overwrite another app's key, expose the
shared account key to all apps, or hand-edit generated app env files. Restricted
keys limit API permissions, not necessarily access to objects belonging to other
apps in the same Stripe account.

Each webhook endpoint has its own signing secret; provision it separately under
an app-specific name. No webhook or payment integration is created just by saving
a Stripe API key. Avoid logging credentials or entire sensitive event payloads.

## App setup

Agree product, currency, price, one-off/subscription behavior and what a purchase
unlocks. Use test credentials and test payments first. Keep test/live keys, prices
and webhook secrets distinct. Verify webhook signatures and handle duplicate
events idempotently; do not unlock paid features solely from a success redirect.
Record configuration names, product/price IDs, verification and remaining steps in
the app's concise runbook. Live activation requires explicit owner authorization.

Reference documentation: https://docs.stripe.com/keys and
https://docs.stripe.com/checkout/fulfillment .
