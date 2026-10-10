# Provider defaults for experiments

Available integrations include OpenAI, Google Gemini, Replicate, OpenRouter and
Anthropic. None is configured merely by cloning this repository. The owner selects
providers in .local/settings.txt. Configured keys live in root-only `/etc/lab/secrets.env`; grant only the keys
needed by a backend through `newlab --secrets` or `labctl secrets-grant`.

| Task | Default provider | Key name |
| --- | --- | --- |
| Transcribe audio | OpenAI | OPENAI_API_KEY |
| General text tasks | OpenAI, unless requested otherwise | OPENAI_API_KEY |
| Image/video understanding or Google-specific features | Gemini | GEMINI_API_KEY |
| Specialist models available on Replicate | Replicate | REPLICATE_API_TOKEN |
| Models accessed through OpenRouter (when selected) | OpenRouter | OPENROUTER_API_KEY |
| Payments (only when requested) | Stripe | STRIPE_SECRET_KEY (separate root-only file; see payments.md) |
| Transactional email (only when selected) | Resend | RESEND_API_KEY |

These are agent implementation defaults, not an automatic runtime router or
permission to send arbitrary data to every provider. Record the chosen model,
version, purpose and relevant costs in each experiment. Use server-side calls;
never expose provider keys in static JavaScript. No provider API requests are
needed for platform installation, and key presence does not verify account
billing, model access or rate limits.

For initial provisioning, `tools/import-credentials.py` imports the owner's
root-only staged files into installed config without printing values. It also
configures hosted ntfy from the staged ntfy.env. This is an administrator step,
not a command available to app runtime identities. Keep source control secret-free.

For email sender configuration, grants and delivery checks, see [email.md](email.md).

## Optional OpenRouter

Select openrouter in AI_PROVIDERS in settings.txt only when desired. During initial
provisioning, enter OPENROUTER_API_KEY in the root-owned 0600 staging file
/root/lab-credentials/providers.env, never in settings.txt or Git. The existing
importer accepts this optional key without requiring other providers. Notification import is independent. For
an existing host, the administrator securely merges this key into
/etc/lab/secrets.env while preserving other keys.

Grant only to backends that need it: `newlab NAME --app --secrets OPENROUTER_API_KEY`
or `sudo /usr/local/sbin/labctl secrets-grant OPENROUTER_API_KEY NAME` followed by
`sudo /usr/local/sbin/labctl service restart NAME`. Keep requests server-side.
Choose the model explicitly and record it in the app runbook; existing direct
provider defaults do not change. Key presence does not verify model access or
credit balance. Paid verification needs an agreed budget.

Stripe has a separate access workflow: see [payments.md](payments.md).
