# Proposed private setup wizard

Design proposal only: no web wizard or automatic provider discovery is implemented
by this document. The existing installation entry point remains SETUP.md. Reuse
its settings, importer and verification steps instead of creating a second installer.

## Form sections

| Section | Inputs | Purpose / readiness check |
| --- | --- | --- |
| Your lab | Name, domain, server address, SSH port, timezone, desktop agent choice | Confirm machine and DNS; distinguish administrator setup from lab experiment access. |
| Notifications — recommended | ntfy server URL (default https://ntfy.sh), a newly generated topic; phone subscription instructions | Send one agreed test and ask whether it arrived. No API key needed for the current anonymous-topic setup. |
| AI — optional | Separate toggles and secret fields for OPENAI_API_KEY, GEMINI_API_KEY, REPLICATE_API_TOKEN, OPENROUTER_API_KEY, ANTHROPIC_API_KEY | Explain capabilities and key creation for each selected provider. Check credentials without paid inference where possible; agree a test budget before paid checks. |
| Backups — recommended | Backblaze B2 bucket, endpoint, key ID, application key; unique repository and Restic encryption password | Confirm recovery details saved off-server, then backup and restore a small test file. Also collect schedule, timezone and retention. |
| Backup monitoring — recommended | Healthchecks.io ping URL | Detect missed backups externally, including when this server cannot send an alert. Verify the owner's alert channel. |
| Email — optional | Resend API key, verified sending domain, default sender | Check domain readiness and authorized test delivery. |
| GitHub — optional | Account/repositories and interactive authentication | Prefer a login flow; do not ask for an unrestricted personal token by default. |
| Payments — advanced, off by default | Stripe test secret key; app-specific configuration and webhook signing secret only if the app uses webhooks | Test mode first. Live payments are a separate explicit choice. |

Coding-agent account login is separate from API keys used by hosted apps. A desktop
subscription does not itself configure an application's paid API access.

## Notification behavior

ntfy is the normal phone channel for app building/ready messages and configured
backup status. Prioritize it in onboarding, but allow an explicit skip and show
that notifications remain unconfigured. A secret random topic is not authenticated
access control: anyone who learns it can read or publish. Never send secrets or
sensitive app content. Authenticated ntfy topics/tokens need implementation work in
the existing notifier/importer before the wizard can advertise support for them.
A server cannot notify through ntfy when it is offline; use external monitoring for
missed check-ins. ntfy does not automatically report every agent event.

## Service state and secret handling

Show Not configured / Saved, untested / Verified / Needs attention. A nonempty key
alone does not establish billing, model access or service health. Publish a
non-secret capability summary for agents; grant each app only the secrets it needs.
Do not automatically enable every model, send user data or incur charges when a
key is saved. Budget preferences are not enforced spending caps.

Serve the wizard privately through authenticated access over Tailscale HTTPS or
an SSH tunnel; require a one-time setup credential even on a private network.
Keep secrets server-side in the existing protected files, never in Git, logs,
chat, browser storage or a status response. Do not run the web app as an unrestricted
root shell: use narrowly defined privileged operations with input validation,
CSRF protection and redacted errors. Preserve existing keys when adding services.
Allow replacing/revoking keys without revealing saved values. Disable initial
setup access when complete; later settings require fresh authentication.

The first release should wrap the existing agent-assisted setup and selected
integrations. Ubuntu compatibility, live service verification and recovery tests
still have to pass independently of the form.
