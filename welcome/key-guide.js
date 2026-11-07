function rawKeyCommands(os, filename = 'id_ed25519') {
  // Filenames are application constants, never user input.
  if (!['id_ed25519', 'lab_ed25519'].includes(filename)) throw new Error('Unknown key filename');
  if (os === 'windows') return {
    path: `~/.ssh/${filename}`,
    copy: `$labKey = "$env:USERPROFILE\\.ssh\\${filename}.pub"\ntry {\n  if (Test-Path -LiteralPath $labKey -PathType Leaf -ErrorAction Stop) {\n    $labPublicKey = Get-Content -LiteralPath $labKey -Raw -ErrorAction Stop\n    if ([string]::IsNullOrWhiteSpace($labPublicKey)) { throw 'Empty public-key file' }\n    Set-Clipboard -Value $labPublicKey -ErrorAction Stop\n    Write-Output 'SUCCESS: Public key copied. Return to the page and paste with Ctrl+V.'\n  } else {\n    Write-Output 'MISSING: Public-key file not found. Click MISSING / No such file on the page.'\n  }\n} catch {\n  Write-Output 'ERROR: Could not read or copy the key. Open the other-error help on the page.'\n}`,
    create: `try {\n  if ((Test-Path "$env:USERPROFILE\\.ssh\\lab_ed25519" -ErrorAction Stop) -or (Test-Path "$env:USERPROFILE\\.ssh\\lab_ed25519.pub" -ErrorAction Stop)) {\n    Write-Output 'EXISTS: A lab key already exists. Nothing was overwritten. Try the copy command below.'\n  } else {\n    Get-Command ssh-keygen -ErrorAction Stop | Out-Null\n    New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\\.ssh" -ErrorAction Stop | Out-Null\n    ssh-keygen -t ed25519 -f "$env:USERPROFILE\\.ssh\\lab_ed25519" -C 'my-lab'\n    if ($LASTEXITCODE -eq 0) { Write-Output 'CREATED: Now run the copy command below.' }\n    else { Write-Output 'ERROR: Key creation failed. Open the other-error help on the page.' }\n  }\n} catch {\n  Write-Output 'ERROR: Key creation failed. Open the other-error help on the page.'\n}`
  };
  return {
    path: `~/.ssh/${filename}`,
    copy: `if [ ! -e "$HOME/.ssh/${filename}.pub" ]; then\n  echo 'MISSING: Public-key file not found. Click MISSING / No such file on the page.'\nelif [ -s "$HOME/.ssh/${filename}.pub" ] && pbcopy < "$HOME/.ssh/${filename}.pub"; then\n  echo 'SUCCESS: Public key copied. Return to the page and paste with Command+V.'\nelse\n  echo 'ERROR: Could not read or copy the key. Open the other-error help on the page.'\nfi`,
    create: `if [ -e "$HOME/.ssh/lab_ed25519" ] || [ -L "$HOME/.ssh/lab_ed25519" ] || [ -e "$HOME/.ssh/lab_ed25519.pub" ] || [ -L "$HOME/.ssh/lab_ed25519.pub" ]; then\n  echo 'EXISTS: A lab key already exists. Nothing was overwritten. Try the copy command below.'\nelif mkdir -p "$HOME/.ssh" && ssh-keygen -t ed25519 -f "$HOME/.ssh/lab_ed25519" -C 'my-lab'; then\n  echo 'CREATED: Now run the copy command below.'\nelse\n  echo 'ERROR: Key creation failed. Open the other-error help on the page.'\nfi`
  };
}

// Assemble the marker at runtime so it occurs only in terminal output, never
// verbatim in the pasted command. Print exactly one final result.
export function keyCommands(os, filename = 'id_ed25519') {
  const commands = rawKeyCommands(os, filename);
  const emphasize = command => os === 'windows'
    ? command.replaceAll('Write-Output ', '$labCopyResult = ') + `\nWrite-Host ''; Write-Host ''; Write-Host ''\nWrite-Host ('RES' + 'ULT---> ' + $labCopyResult) -ForegroundColor Cyan\nWrite-Host ''; Write-Host ''`
    : command.replaceAll('echo ', 'lab_copy_result=') + `\nprintf '\\n\\n\\n\\033[1m%s%s\\033[0m\\n\\n\\n' 'RES' "ULT---> $lab_copy_result"`;
  return {...commands, copy: emphasize(commands.copy), create: emphasize(commands.create)};
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
  const setPath = filename => {
    $('key-path').value = keyCommands($('computer-os').value, filename).path;
    updateConnection();
  };
  function render() {
    const os = $('computer-os').value;
    const current = keyCommands(os);
    const fresh = keyCommands(os, 'lab_ed25519');
    $('find-key').textContent = current.copy;
    $('create-key').textContent = fresh.create;
    $('new-key').textContent = fresh.copy;
    $('terminal-instructions').textContent = os === 'windows'
      ? 'Open Windows PowerShell from the Start menu. Use Ctrl+V to paste commands, then press Enter.'
      : 'Open Terminal on your Mac (Applications → Utilities → Terminal). Use ⌘V to paste commands, then press Enter.';
    $('create-key-panel').hidden = true;
    $('paste-help').hidden = true;
    setPath('id_ed25519');
  }
  function ready(filename) {
    setPath(filename);
    $('paste-help').textContent = 'Your public key is now on your clipboard. Click the public-key field below and paste: ⌘V on Mac, Ctrl+V on Windows. Do not run the create-key command.';
    $('paste-help').hidden = false;
    $('create-key-panel').hidden = true;
    $('public-key').focus({preventScroll: true});
    $('paste-help').scrollIntoView({behavior: 'smooth', block: 'center'});
  }
  $('computer-os').addEventListener('change', render);
  $('key-found').addEventListener('click', () => ready('id_ed25519'));
  $('key-missing').addEventListener('click', () => {
    $('paste-help').hidden = true;
    $('create-key-panel').hidden = false;
    $('create-key-panel').scrollIntoView({behavior: 'smooth', block: 'start'});
  });
  $('new-key-found').addEventListener('click', () => ready('lab_ed25519'));
  render();
}
