export const KEY_PATH = '~/.ssh/infinity_machine_ed25519';

export function keyCommands(os) {
  const copy = os === 'windows' ? `$infinityKey = "$env:USERPROFILE\\.ssh\\infinity_machine_ed25519"
try {
  Get-Command ssh-keygen -ErrorAction Stop | Out-Null
  Get-Command Set-Clipboard -ErrorAction Stop | Out-Null
  $privateExists = Test-Path -LiteralPath $infinityKey
  $publicExists = Test-Path -LiteralPath "$infinityKey.pub"
  if ($privateExists -or $publicExists) {
    if (!(Test-Path -LiteralPath $infinityKey -PathType Leaf) -or !(Test-Path -LiteralPath "$infinityKey.pub" -PathType Leaf)) {
      throw 'Incomplete key pair. Keep the existing files and ask your setup agent for help.'
    }
  } else {
    New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\\.ssh" -ErrorAction Stop | Out-Null
    ssh-keygen -t ed25519 -f $infinityKey -C 'infinity-machine'
    if ($LASTEXITCODE -ne 0) { throw 'Key creation did not finish.' }
  }
  ssh-keygen -l -f "$infinityKey.pub" | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'The public-key file is invalid.' }
  $infinityPublicKey = Get-Content -LiteralPath "$infinityKey.pub" -Raw -ErrorAction Stop
  if ([string]::IsNullOrWhiteSpace($infinityPublicKey)) { throw 'The public-key file is empty.' }
  Set-Clipboard -Value $infinityPublicKey -ErrorAction Stop
  $infinityResult = 'SUCCESS: Key copied to clipboard. Return to the form and paste with Ctrl+V.'
} catch {
  $infinityResult = 'ERROR: ' + $_.Exception.Message + ' Nothing was submitted. Do not paste until copying succeeds.'
}
Write-Host ''; Write-Host ''; Write-Host ''
Write-Host ('RES' + 'ULT---> ' + $infinityResult) -ForegroundColor Cyan
Write-Host ''; Write-Host ''; Write-Host ''` : `(
infinity_key="$HOME/.ssh/infinity_machine_ed25519"
infinity_prepare_key() {
  command -v ssh-keygen >/dev/null && command -v pbcopy >/dev/null || return 1
  if [ -L "$infinity_key" ] || [ -L "$infinity_key.pub" ]; then
    echo 'Keep existing key links unchanged; ask your setup agent for help.'
    return 1
  fi
  if [ -e "$infinity_key" ] || [ -e "$infinity_key.pub" ]; then
    if [ ! -f "$infinity_key" ] || [ ! -s "$infinity_key" ] || [ ! -f "$infinity_key.pub" ] || [ ! -s "$infinity_key.pub" ]; then
      echo 'Incomplete key pair. Keep the existing files and ask your setup agent for help.'
      return 1
    fi
  else
    mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh" || return 1
    ssh-keygen -t ed25519 -f "$infinity_key" -C 'infinity-machine' || return 1
  fi
  ssh-keygen -l -f "$infinity_key.pub" >/dev/null || return 1
  pbcopy < "$infinity_key.pub"
}
if infinity_prepare_key; then
  infinity_result='SUCCESS: Key copied to clipboard. Return to the form and paste with Command+V.'
else
  infinity_result='ERROR: Could not prepare or copy the key. See the message above. Do not paste until copying succeeds.'
fi
printf '\\n\\n\\n\\033[1m%s%s\\033[0m\\n\\n\\n\\n' 'RES' "ULT---> $infinity_result"
)`;
  return {path: KEY_PATH, copy};
}

export function privateKeyArgument(path, os) {
  if (os === 'windows') {
    const quote = value => "'" + value.replaceAll("'", "''") + "'";
    return path.startsWith('~/') ? '(Join-Path $HOME ' + quote(path.slice(2)) + ')' : quote(path);
  }
  const quote = value => "'" + value.replaceAll("'", "'\\''") + "'";
  return path.startsWith('~/') ? '"$HOME"/' + quote(path.slice(2)) : quote(path);
}

export function initKeyGuide(updateConnection) {
  const $ = id => document.getElementById(id);
  function render() {
    const os = $('computer-os').value;
    const current = keyCommands(os);
    $('find-key').textContent = current.copy;
    $('command-preview').textContent = current.copy.split('\n').slice(0, 3).join('\n');
    $('key-path').value = current.path;
    $('ssh-key-path').textContent = current.path;
    $('terminal-instructions').textContent = os === 'windows'
      ? 'Open Windows PowerShell. Paste the command with Ctrl+V, then press Enter.'
      : 'Open Terminal on your Mac (Applications → Utilities → Terminal). Paste the command with ⌘V, then press Enter.';
    updateConnection();
  }
  $('computer-os').addEventListener('change', render);
  render();
}
