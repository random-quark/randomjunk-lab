# Provider defaults for experiments

Configured by the owner: OpenAI, Google Gemini, Replicate. Anthropic is not
configured. Keys live in root-only `/etc/lab/secrets.env`; grant only the keys
needed by a backend through `newlab --secrets` or `labctl secrets-grant`.

| Task | Default provider | Key name |
| --- | --- | --- |
| Transcribe audio | OpenAI | OPENAI_API_KEY |
| General text tasks | OpenAI, unless requested otherwise | OPENAI_API_KEY |
| Image/video understanding or Google-specific features | Gemini | GEMINI_API_KEY |
| Specialist models available on Replicate | Replicate | REPLICATE_API_TOKEN |
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
