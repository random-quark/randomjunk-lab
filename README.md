# The Infinity Machine

Describe an app. Get a link. Open it on your phone.

The Infinity Machine turns your own server into a place to build small apps with
an AI agent. Tell Claude what you want to make; it builds, tests and publishes it.
The server supplies hosting, databases and instructions so each idea can start
without another round of infrastructure setup.

[The story behind the project →](https://www.randomquark.com/labs/infinity_machine/)

## 1. Connect Claude to your new server

You need a **fresh Ubuntu 24.04 LTS VPS**, its IP address and root SSH password or
key, plus Claude Desktop with access to the **Code** tab. No domain or API keys
are required to get started.

1. In Claude Desktop, open **Code → New → Choose environment → + New environment**.
2. Select **SSH**, name it **Infinity Machine — Setup**, then choose
   **Host → + Add SSH connection**.
3. Enter `root@YOUR_SERVER_IP` and port **22** (unless your provider specifies
   another). Use your SSH key if you have one; otherwise enter the server’s root
   password when Claude asks. Verify a new host’s fingerprint with your provider.
4. Save the connection, select it under **Host**, and set **Folders** to `/root`.
   Leave **Worktree** unchecked. Click **Create environment** and select it.
5. Below the message box, choose **Auto** for fewer approval prompts, if available.

Claude installs its remote helper automatically. You don’t need tmux or a separate
Claude installation on the server.

## 2. Ask Claude to install The Infinity Machine

Paste this into your new Claude conversation:

> Set up The Infinity Machine on this fresh server. Confirm the hostname, Ubuntu
> version and that you are running as root. Install git if needed, then clone
> https://github.com/random-quark/randomjunk-lab.git into /root/infinity-machine.
> Read its SETUP.md and follow it. Help me complete the private setup form; keep
> API keys and passwords out of chat and Git. Use this server’s actual IP if I
> have no domain. Install and test the system, tell me anything still pending,
> then give me a private invitation link to connect as lab through Claude Desktop.

Claude will ask about the services you want. **ntfy** is useful for sending app
links to your phone; **Replicate** and **OpenAI** are optional AI services. You can
start without them and add them later.

## 3. Open your invitation and start building

1. Open the private invitation Claude gives you. Follow the page to find or create
   your computer’s SSH key, paste its **public** key, and click **Enable access**.
   Optionally connect ntfy for phone notifications, or choose **Skip for now**.
2. In Claude Desktop, add another **SSH** environment named **The Infinity Machine**.
   Use `lab@YOUR_SERVER_IP`, the SSH port and key path shown on the invitation page.
   Set **Folders** to `/srv/lab`, leave **Worktree** unchecked, and create it.
3. Select that environment and choose **Auto** if available. Use **Copy first message**
   on your invitation page—it includes your notification recipient if configured.
   Without notifications, you can simply send:

> Confirm you are running as lab in /srv/lab. Read CLAUDE.md and the installed
> instructions. Help me build my first experiment. Ask me what I want to make.

Use this environment from now on. Keep the root connection for administration.
To invite a trusted friend, ask your setup agent for a new private invitation;
they follow the same page without needing root access. Everyone using `lab`
shares the machine’s apps and files.

**Codex:** Instructions coming.

*For agents: [installation](SETUP.md), [platform development](AGENTS.md),
[technical reference](docs/platform-reference.md).*
