# Connect Claude Desktop to The Infinity Machine

Initial setup uses root (or a sudo administrator) and the repository checkout.
Everyday experiment work uses lab and /srv/lab. Access is authorized per Linux
account; root login does not grant lab login. The temporary test-agent key is not
the owner's laptop key.

## One-time laptop access

The welcome guide has one create-or-copy command for Mac Terminal and Windows
PowerShell. It consistently uses `~/.ssh/infinity_machine_ed25519` (private) and
`~/.ssh/infinity_machine_ed25519.pub` (public). If neither exists, it creates a
key pair with an interactive passphrase prompt, then copies the public key.
If both already exist, it reuses them. Incomplete pairs are preserved and report
an error; the command never deliberately overwrites an existing key.

The full command is copied even while its preview is collapsed to three faded
lines. Click the preview to inspect it. The final emphasized RESULT arrow has
blank lines above/below and reports SUCCESS only after clipboard copying succeeds.
Paste directly into the public-key field (Command+V on Mac, Ctrl+V on Windows).
No SUCCESS/MISSING buttons or second copy command are required. Claude's SSH-key
field and the diagnostic command default to the same dedicated private-key path.
The browser cannot inspect a local key or prove it matches a manually pasted key.

Previously authorized keys remain valid: use their original private-key filename
in Claude, or request a new invitation to enroll the dedicated Infinity Machine
key. An already used invitation cannot enroll a different key. Nothing renames
or removes existing laptop/server keys. Step 6 exposes `/srv/lab` with its own
copy button. A private-key passphrase prompt is not a lab account password prompt.

Windows clipboard handling follows [Microsoft's Set-Clipboard documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/set-clipboard?view=powershell-5.1), with terminating error handling for reads and copies.

The private setup form has a public-key field. After saving, the administrator
runs `python3 -I tools/setup-wizard.py authorize-ssh` from the trusted checkout.
Alternatively, pipe one public key into `/usr/local/sbin/lab-authorize-key` as root.
This fallback helper adds the key for lab without replacing existing keys. The
invitation form below provides the normal recipient flow.

The welcome guide now uses a private invitation for both the owner and invited
friends. Paste the public key and click Enable access; no root command or password
is requested from the person connecting. The server authorizes the key for lab.
An accepted link hides manual code entry and tells the user no second invitation
is needed. Missing or invalid invitations show recovery options. Opening the public
guide alone grants nothing. Invitations expire after 24 hours,
authorize one key, and allow retrying that same key if a response was lost.

After installing the core and publishing the welcome guide, the setup agent runs:

```sh
python3 -I tools/enable-access.py --app welcome
runuser -u lab -- lab-access invite
```

Give the owner the private URL printed by the second command. Do not put it in
Git, public pages, screenshots or shared logs. This is also how the owner adds
their first lab key after installing the server. Once connected, an existing lab
session can run `lab-access invite` to invite another device or friend without
root. Each invitation grants the shared lab account, including its apps/files;
there is no per-person isolation. Keep root administration separate.

`lab-access invite --hours 1` creates a shorter-lived invitation (1–168 hours).
`lab-access revoke --id INVITATION_ID` revokes an invitation; this does not remove
an already installed SSH key. Remove an installed key separately when revoking
someone's existing SSH access.

The enrollment service runs as lab on loopback port 9876, with systemd write
access limited to lab's SSH directory, invitation state and private temporary
files. Only the chosen guide site proxies /_lab/access/* to it. Tokens are hashed
in the private database, transmitted in Authorization headers, and not logged.
The browser takes the token from the URL fragment, removes it from the address
bar and keeps it in memory only. Reopen the original link after refreshing.
Key binding commits before authorization, so interrupted requests cannot redeem
one invitation for another key. No API accepts an account or file destination.

The guide shows three steps: authorize the computer, connect Claude, and start an
experiment. Optional diagnostics are in a collapsed Connection trouble? area below
the Claude card. If needed, test from the laptop with the matching private-key path
and actual host/port:

```sh
ssh -i ~/.ssh/infinity_machine_ed25519 -o IdentitiesOnly=yes -o PreferredAuthentications=publickey lab@YOUR_SERVER 'whoami; cd /srv/lab && pwd'
```

Expected output: lab and /srv/lab. A private-key passphrase prompt is normal. Lab
has no default password. Verify the server's host fingerprint before first trust;
do not disable host-key checks to get past a reinstall warning.

## Claude Desktop clicks

1. Open Code → New → Choose environment → + New environment.
2. Select SSH and give the environment a name such as The Infinity Machine.
3. Under Host, choose + Add SSH connection.
4. Enter the connection name, `lab@YOUR_SERVER`, and SSH port (normally 22).
   In SSH key, choose the matching private-key file on the Mac, without .pub.
   Leave the worktree folder at its default.
5. Save the connection and select it under Host.
6. Under Folders, enter /srv/lab; leave Worktree unchecked.
7. Create environment and select it for the conversation.
8. Below the message box, open the permissions selector and choose **Auto** for
   fewer routine approval prompts. If it already says Auto, you’re set. Claude
   may still ask when needed. If Auto is unavailable, keep the available default.
9. Use **Copy first message** on the invitation page to include the confirmed
   notification recipient. Without notifications, send:

> Confirm you are running as lab in /srv/lab. Read CLAUDE.md and the installed lab
> instructions. Then help me build my first experiment. Ask me what I want to make.

Desktop installs its remote helper automatically. No manual CLI session or tmux is
required. The UI sequence follows owner screenshots from 2026-11-07.
Auto is the permissions selector below the message box, not the cloud environment
option. See [permission modes](https://code.claude.com/docs/en/desktop#choose-a-permission-mode). Connection
fields were checked against [Claude's official guide](https://code.claude.com/docs/en/desktop#ssh-sessions).

## Publish the welcome guide

The reusable public guide assets are under welcome/. After creating a static
welcome app, copy index.html, welcome.css, welcome.js, key-guide.js, refresh.html and
sw.template.js into its public directory
as lab, retaining its generated icons, manifest and pwa.js. Add connection.json
with the actual reachable SSH hostname and integer port, for example:

```json
{"host":"YOUR_SERVER","port":22}
```

Never put key material or administrator credentials in connection.json. The guide
validates host/port before generating commands. Publish through labctl as lab;
this regenerates the offline worker. The page is a guide, not an SSH web gateway.
For a previously installed platform, install the new root-owned sshkeys.py library
and lab-authorize-key helper from reviewed source before publishing the guide.
Do not rerun bootstrap on an existing machine.

The welcome guide uses its own network-first service worker so updated access
instructions replace retired ones. It does not change experiment service workers.
If an older guide is cached, open /refresh.html with the same invitation fragment;
it upgrades the worker and returns to the current guide without exposing the token
in a query string. It never automatically reloads an active enrollment form.


After enrollment, the optional ntfy panel creates a separate subscription for
that SSH public key. The user can skip, or subscribe through the phone app and
confirm test receipt. The page adds the confirmed recipient ID to the first
Claude message; no owner destination is overwritten. See notifications.md.
