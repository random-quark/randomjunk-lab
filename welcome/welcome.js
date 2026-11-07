const $ = id => document.getElementById(id);
const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
let connection;
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
$('public-key').addEventListener('input', () => { $('grant').hidden = true; $('grant-command').textContent = ''; });
$('prepare').addEventListener('click', () => {
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
  $('grant-command').textContent = `printf '%s\\n' ${quote(key)} | ssh -p ${connection.port} root@${connection.host} /usr/local/sbin/lab-authorize-key`;
  $('grant').hidden = false;
});
for (const button of document.querySelectorAll('[data-copy]')) button.addEventListener('click', async () => {
  const text = $(button.dataset.copy).textContent;
  try { await navigator.clipboard.writeText(text); $('copy-status').textContent = 'Copied. Paste it where the instructions indicate.'; }
  catch { $('copy-status').textContent = 'Select the text and copy it manually.'; }
});
