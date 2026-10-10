# Sharing the platform source

Give new owners **SETUP.md**. The tracked questionnaire and checklist are templates;
actual choices belong in ignored `.local/` copies. All secret input stays outside
the checkout in protected files. Each machine needs its own accounts, restricted
keys, domain/DNS and distinct backup repository and recovery password.

The original GitHub repository is private unless its owner changes visibility.
Grant selected collaborators access through GitHub, or provide a source-only archive.
Do not share the whole working directory, `/root`, `/home/lab`, `/etc/lab`, Restic
configuration, browser profiles, SSH keys, CLI logins or generated experiments.
Never copy secrets into `.local/` merely because it is ignored.

After reviewing and committing intended source changes, create an archive with:

```sh
git archive --format=zip --prefix=randomjunk-lab/ --output=../randomjunk-lab-source.zip HEAD
```

That includes tracked source only, without Git history, `.local/`, virtualenvs or
untracked files. GitHub Download ZIP likewise exports tracked files. A Git clone
includes reachable history; deleting a leaked key in a later commit does not
remove it from that history. If a credential is ever detected, rotate/revoke it
first and agree a history-cleanup plan before sharing; do not silently rewrite Git.

## Audit on 2026-10-10

- Gitleaks 8.30.1, official release checksum verified: all 28 reachable commits
  before this revision scanned, with no findings. No custom exclusions/allowlist.
- Separate in-memory comparison of 12 current protected provider/notification/
  backup credential values against all 296 historical blobs: no matches. Values
  were neither printed nor copied into this repository.
- Current distributable source also scanned; no findings. Local audit reports and
  downloaded scanner stay outside the repo. No production credentials were changed.
- Historical documents still name the original public domain/IP, GitHub identity,
  experiment names and installation dates. These are not credentials; this is a
  secret audit, not anonymisation of the project's history.

A clean scan is evidence, not a guarantee. It covers this local repository's
reachable history and distributable files, not GitHub issues, releases, Actions
logs, attachments, inaccessible remote refs or credentials previously pasted in
chat. Recheck after future changes. Keep the repo private until you choose otherwise.

## Repeat the scanner checks

With a trusted Gitleaks executable available (use official release checksums):

```sh
gitleaks git . --log-opts="--all --full-history" --redact=100
```

Also extract the intended source archive into a temporary directory and run
`gitleaks dir EXTRACTED_DIRECTORY --redact=100`. Do not scan/print live secret-file
contents to a shared terminal or add raw reports to Git. Review tracked file names
and any changes to examples, integration URLs, local settings or ignore rules.
