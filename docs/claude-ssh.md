# Connect Claude Desktop to your installed lab

Initial setup uses root (or a sudo administrator) and the repository checkout.
Everyday experiment work uses lab and /srv/lab. Access is authorized per Linux
account; root login does not grant lab login. The temporary test-agent key is not
the owner's laptop key.

## One-time laptop access

On the owner's Mac, copy the public key with `pbcopy < ~/.ssh/id_ed25519.pub`.
If it is missing, create a dedicated key with
`ssh-keygen -t ed25519 -f ~/.ssh/lab_ed25519 -C "my-lab"`, without overwriting an
existing file. Then copy `~/.ssh/lab_ed25519.pub`. Use a passphrase when prompted.
The private file stays on the Mac; only the .pub contents go to the administrator.

The private setup form has a public-key field. After saving, the administrator
runs `python3 -I tools/setup-wizard.py authorize-ssh` from the trusted checkout.
Alternatively, pipe one public key into `/usr/local/sbin/lab-authorize-key` as root.
This helper adds the key for lab without replacing existing keys. It is not part
of lab's sudo allowlist and has no public HTTP endpoint.

The public welcome guide provides a local-only key field and a copyable command
that sends the public key over authenticated root SSH to that helper. The browser
neither sends the key to an HTTP service nor saves it. Preparing the command does
not authorize anything; the owner must execute it with administrator access.

Test from the Mac with the matching private-key path and actual host/port:

```sh
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o PreferredAuthentications=publickey lab@YOUR_SERVER 'whoami; cd /srv/lab && pwd'
```

Expected output: lab and /srv/lab. A private-key passphrase prompt is normal. Lab
has no default password. Verify the server's host fingerprint before first trust;
do not disable host-key checks to get past a reinstall warning.

## Claude Desktop clicks

1. Open Code → New → Choose environment → + New environment.
2. Select SSH and give the environment a name such as My Lab.
3. Under Host, choose + Add SSH connection.
4. Enter the connection name, `lab@YOUR_SERVER`, and SSH port (normally 22).
   In SSH key, choose the matching private-key file on the Mac, without .pub.
   Leave the worktree folder at its default.
5. Save the connection and select it under Host.
6. Under Folders, enter /srv/lab; leave Worktree unchecked.
7. Create environment, select it for the conversation, and send:

> Confirm you are running as lab in /srv/lab. Read CLAUDE.md and the installed lab
> instructions. Then help me build my first experiment. Ask me what I want to make.

Desktop installs its remote helper automatically. No manual CLI session or tmux is
required. The UI sequence follows owner screenshots from 2026-11-07; connection
fields were checked against [Claude's official guide](https://code.claude.com/docs/en/desktop#ssh-sessions).

## Publish the welcome guide

The reusable public guide assets are under welcome/. After creating a static
welcome app, copy index.html, welcome.css and welcome.js into its public directory
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
