# Lab server v2: browser-based onboarding

Status: proposed; implementation has not started.
Plan recorded: 3 November 2026.

## Purpose

Make the existing randomjunk-lab platform easier for someone without server
administration experience to install and use. The intended user wants to create
and host experiments like the owner's current lab.

For someone who only wants an agent to update one existing website, this platform
is probably more than they need. Prefer their existing hosting, source repository,
and a simple preview/publish workflow unless they need multiple apps or backends.

## Proposed experience

1. Rent a fresh server using a supported operating-system image.
2. Run one documented bootstrap command. It installs the minimum required setup
   service and provides a temporary setup link.
3. Open the link in a browser and complete a guided wizard:
   - Administrator access and server/domain configuration.
   - API credentials for desired services, with clear Skip options.
   - Connection checks with understandable success/failure messages.
   - HTTPS, backups, and remaining setup requirements.
4. Follow instructions to connect the coding agent.
5. Create and publish a first experiment, then verify it works.
6. Use a small authenticated administration page later to replace, test, or remove
   credentials and configure additional services.

The browser replaces manual discovery and editing of configuration files. It does
not replace the existing protected server storage or per-application credential
access controls.

## Architecture and scope

Build a thin onboarding layer over the existing installer and setup workflow.
Keep one source of installation logic rather than a second, divergent web
installer. First inspect README.md, SETUP.md, AGENTS.md, the settings workflow,
and existing helpers to identify reusable operations and gaps.

The first version should provide:

- A minimal bootstrap entry point and temporary setup session.
- A browser wizard for the existing supported setup choices.
- Optional provider credentials with masked entry and explicit validation.
- Progress, clear error reporting, and safe retry/resume after interruption.
- A completion checklist that distinguishes verified steps from pending work.
- A small administrator interface for credential management after installation.
- Instructions for connecting the agent and creating a first experiment.

Avoid building a general hosting control panel, billing service, or a separate
agent product. Do not require credentials for services the user does not need.
Paid validation calls, if necessary, must be clearly identified before running.

## Security requirements and open design decisions

The highest-risk boundary is initial setup, before a domain and HTTPS are ready.
Choose and test a secure bootstrap approach before implementing credential entry.
Possible approaches include an SSH tunnel for initial local access or a minimal
HTTPS setup stage. Do not accept API keys over unprotected public HTTP.

- Use temporary, high-entropy setup access with expiry and revocation.
- Prevent setup takeover, token disclosure through logs/referrers, CSRF, and
  replay after setup completes.
- Establish authenticated administrator access before closing bootstrap access.
- Do not leave an unauthenticated public configuration endpoint after setup.
- Never return saved API key values to the browser. Show configured status and
  Replace, Test, and Remove actions instead.
- Exclude secrets from logs, source control, screenshots, and diagnostic output.
- Preserve protected credential storage and per-app grants; do not give the web
  process unrestricted root command execution.
- Use narrowly scoped, validated privileged operations rather than shell commands
  assembled from form input.
- Preserve safe configuration and recoverability when an operation fails or the
  browser/server disconnects. Re-running setup must not duplicate services or
  silently overwrite working configuration.

Decide the supported OS, DNS prerequisites, administrator authentication method,
backup choices, and credential-validation behavior during implementation planning.
Explain unavoidable DNS or provider-console steps in the wizard; do not imply
that every external prerequisite can be automated.

## Delivery stages

1. **Review and design:** map existing installation steps, define supported inputs,
   security boundaries, bootstrap access, and recovery behavior.
2. **Prepare implementation:** build the bootstrap, wizard, and restricted installer
   integration; add isolated security, validation, and interruption tests.
3. **Prepare a test checklist:** document the exact fresh-server journey and expected
   outcomes before asking the owner to rent a server.
4. **Fresh-server trial:** the owner rents a separate server for one month. Install
   from scratch using the published instructions and record actual results.
5. **Refine and retest:** fix confusing steps and failures, then repeat on a clean
   installation rather than relying on a previously configured machine.
6. **Document and hand off:** provide concise onboarding, maintenance, recovery,
   and teardown guidance, with known limitations clearly recorded.

The existing production lab must remain untouched by the trial. A successful
installation on the current machine is not evidence that onboarding works on a
fresh server.

## Fresh-server acceptance checklist

- [ ] A clean supported server can start setup with one documented command.
- [ ] The temporary browser link works and rejects invalid or expired access.
- [ ] Credentials are entered only over an authenticated, encrypted connection.
- [ ] Optional services can be skipped without blocking unrelated functionality.
- [ ] Invalid credentials, missing DNS, and unavailable providers produce useful errors.
- [ ] Refreshing the browser or interrupting installation can be recovered safely.
- [ ] Re-running completed steps does not damage or duplicate configuration.
- [ ] Saved secrets cannot be retrieved through the UI or found in logs/source.
- [ ] Administrator authentication works and bootstrap access is disabled afterward.
- [ ] The coding agent connects using the documented workflow.
- [ ] A first experiment can be created, published over HTTPS, and accessed.
- [ ] Configured app credentials are available only to authorized apps.
- [ ] Configured backups run, and a representative restore is actually tested.
- [ ] Restart/reboot behavior and basic health checks pass.
- [ ] Setup usability is checked with someone unfamiliar with the platform.

## Trial cost and teardown

Prepare the implementation and checklist before renting the test server so that
paid time is used for validation. The owner will arrange the rental and later
cancellation; this plan does not authorize provisioning or charges.

Use separate trial credentials where practical. Before cancellation, export any
wanted results, revoke trial credentials or grants, remove sensitive data, clean
up test DNS and related external resources, and document what was retained.
Provider cancellation remains an explicit owner action unless separately authorized.

## Next action

Resume with the review/design stage and turn this plan into a concrete implementation
and test checklist. Do not rent a server, deploy the wizard, or alter production
merely because this planning document exists.
