const $ = id => document.getElementById(id);
const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
let connection;
function readInvitation() {
  const value = new URLSearchParams(location.hash.slice(1)).get('invite') || '';
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  return value;
}
let invitation = readInvitation();
let invitationReady = false;
let sending = false;
async function access(action, data = {}) {
  const response = await fetch('/_lab/access/' + action, {
    method: 'POST', cache: 'no-store', credentials: 'omit',
    headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + invitation},
    body: JSON.stringify(data)
  });
  let result;
  try { result = await response.json(); }
  catch { throw new Error('Access setup is unavailable. Ask the server owner to check it.'); }
  if (!response.ok) throw new Error(result.error || 'Could not enable access.');
  return result;
}
async function checkInvitation() {
  invitationReady = false;
  $('prepare').disabled = true;
  if (!invitation) return;
  try {
    const status = await access('status');
    invitationReady = true;
    $('invite-status').textContent = status.used ? 'This invitation has already enabled one key. You can retry that same key or continue to step 2.' : 'Your invitation is ready. Paste your public key below.';
    $('invite-entry').open = false;
    $('prepare').disabled = !connection;
  } catch (error) { $('invite-status').textContent = error.message; }
}
window.addEventListener('hashchange', async () => {
  const value = readInvitation();
  if (value) { invitation = value; await checkInvitation(); }
});
$('use-invite').addEventListener('click', async () => {
  invitation = $('invite-code').value.trim();
  $('invite-code').value = '';
  await checkInvitation();
});
const buttons = [...document.querySelectorAll('button[data-copy], #prepare, #test-command-button')];
buttons.forEach(button => { button.disabled = true; });
try {
  const response = await fetch('/connection.json', {cache: 'no-store'});
  if (!response.ok) throw new Error();
  connection = await response.json();
  if (!/^[a-zA-Z0-9.-]+$/.test(connection.host) || !Number.isInteger(connection.port) || connection.port < 1 || connection.port > 65535) throw new Error();
  $('ssh-host').textContent = `lab@${connection.host}`;
  $('ssh-port').textContent = String(connection.port);
  buttons.forEach(button => { button.disabled = false; });
  $('prepare').disabled = true;
  await checkInvitation();
} catch { $('key-error').textContent = 'Connection details could not load. Reload this page while online.'; }
function testCommand() {
  const path = $('key-path').value.trim();
  if (!path || path.endsWith('.pub') || /[\r\n]/.test(path)) {
    $('test-command').textContent = 'Enter the private-key file path, without .pub.';
    return;
  }
  const shellPath = path.startsWith('~/') ? '"$HOME"/' + quote(path.slice(2)) : quote(path);
  $('ssh-key-path').textContent = path;
  $('test-command').textContent = `ssh -i ${shellPath} -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -p ${connection.port} lab@${connection.host} 'whoami; cd /srv/lab && pwd'`;
}
$('test-command-button').addEventListener('click', testCommand);
$('key-path').addEventListener('input', () => { if (connection) testCommand(); });
if (connection) testCommand();
$('public-key').addEventListener('input', () => { $('grant').hidden = true; });
$('prepare').addEventListener('click', async () => {
  if (!invitationReady || sending) return;
  const value = $('public-key').value.trim();
  const parts = value.split(/\s+/);
  $('grant').hidden = true;
  if (/[\r\n]/.test(value) || value.length > 16384 || parts.length < 2 || !/^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521))$/.test(parts[0]) || !/^[A-Za-z0-9+/]+={0,2}$/.test(parts[1])) {
    $('key-error').textContent = 'Paste one OpenSSH public key (.pub), beginning ssh-ed25519, ssh-rsa or ecdsa-sha2-. Never paste a private key.';
    return;
  }
  try {
    const bytes = Uint8Array.from(atob(parts[1]), c => c.charCodeAt(0));
    const length = new DataView(bytes.buffer).getUint32(0);
    if (length > bytes.length - 4 || new TextDecoder().decode(bytes.slice(4, 4 + length)) !== parts[0]) throw new Error();
  } catch { $('key-error').textContent = 'That public key looks incomplete. Copy the whole .pub file again.'; return; }
  $('key-error').textContent = '';
  const key = parts.slice(0, 2).join(' ');
  sending = true;
  $('prepare').disabled = true;
  $('prepare').textContent = 'Enabling…';
  try {
    await access('enroll', {public_key: key});
    $('public-key').value = '';
    $('grant').hidden = false;
    $('invite-status').textContent = 'Access enabled for this key. This invitation cannot add another key.';
  } catch (error) { $('key-error').textContent = error.message; }
  finally {
    sending = false;
    $('prepare').disabled = false;
    $('prepare').textContent = 'Enable access';
  }
});
for (const button of document.querySelectorAll('[data-copy]')) button.addEventListener('click', async () => {
  const text = $(button.dataset.copy).textContent;
  try { await navigator.clipboard.writeText(text); $('copy-status').textContent = 'Copied. Paste it where the instructions indicate.'; }
  catch { $('copy-status').textContent = 'Select the text and copy it manually.'; }
});
