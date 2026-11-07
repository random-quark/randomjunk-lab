'use strict';
let token = '';
let state = null;
let dirty = false;
let busy = false;
const removed = new Set();
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const providers = [
  ['Gemini', 'GEMINI_API_KEY', 'Google models for text and multimodal apps.', 'https://aistudio.google.com/api-keys'],
  ['Anthropic', 'ANTHROPIC_API_KEY', 'Use Claude models in your hosted apps.', 'https://console.anthropic.com/settings/keys'],
  ['OpenRouter', 'OPENROUTER_API_KEY', 'Access its supported model catalog through one account.', 'https://openrouter.ai/settings/keys'],
];
for (const [name, key, description, url] of providers) {
  const section = document.createElement('section');
  const title = document.createElement('h3'); title.textContent = name;
  const p = document.createElement('p'); p.textContent = description; p.className = 'small';
  const label = document.createElement('label'); label.textContent = `${name} API key`;
  const input = document.createElement('input'); input.type = 'password'; input.dataset.secret = key;
  input.autocomplete = 'new-password'; input.spellcheck = false; input.placeholder = `Paste your ${name} key`;
  label.append(input);
  const footer = document.createElement('div'); footer.className = 'key-footer';
  const link = document.createElement('a'); link.textContent = 'Get a key ↗'; link.href = url; link.target = '_blank'; link.rel = 'noreferrer';
  const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'text-button'; remove.dataset.remove = key; remove.hidden = true; remove.textContent = 'Remove from setup';
  footer.append(link, remove);
  const status = document.createElement('span'); status.className = 'status'; status.dataset.status = key; status.textContent = 'Not configured';
  section.append(title, p, label, footer, status); $('#other-providers').append(section);
}
// Give every additional secret field the same saved/replace/remove behavior.
for (const input of $$('[data-secret]')) {
  if ($(`[data-status="${input.dataset.secret}"]`)) continue;
  const status = document.createElement('span'); status.className = 'status'; status.dataset.status = input.dataset.secret;
  const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'text-button'; remove.dataset.remove = input.dataset.secret;
  remove.textContent = 'Remove from setup'; remove.hidden = true;
  input.parentElement.append(status, document.createTextNode(' '), remove);
}
function message(text, error = false) {
  $('#message').textContent = text; $('#message').classList.toggle('error', error); $('#message').hidden = false;
}
async function api(action, body) {
  const response = await fetch(`/api/${action}`, {
    method: body === undefined ? 'GET' : 'POST', cache: 'no-store',
    headers: {Authorization: `Bearer ${token}`, ...(body === undefined ? {} : {'Content-Type': 'application/json'})},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  let data;
  try { data = await response.json(); } catch { throw new Error('The setup server is unavailable. Reconnect and try again.'); }
  if (!response.ok) throw new Error(data.error || 'Setup could not complete this action.');
  return data;
}
function panels() {
  $('#ntfy-panel').hidden = $('#notifications').value !== 'ntfy';
  $('#backup-fields').hidden = $('#backups').value !== 'b2';
  $('#monitor-fields').hidden = $('#monitoring').value !== 'healthchecks';
  $('#email-fields').hidden = $('#email').value !== 'resend';
  $('#stripe-fields').hidden = $('#payments').value !== 'stripe';
}
function render(next, fillChoices = true) {
  state = next;
  if (fillChoices) {
    for (const input of $$('[data-choice]')) input.value = next.choices[input.dataset.choice] || '';
    $('#recovery').checked = next.choices.RECOVERY_DETAILS_SAVED === 'yes';
  }
  for (const input of $$('[data-secret]')) {
    const saved = next.saved_keys.includes(input.dataset.secret);
    input.placeholder = saved ? 'Saved — leave blank to keep, or paste a replacement' : 'Paste a key when needed';
    const badge = $(`[data-status="${input.dataset.secret}"]`);
    badge.textContent = saved ? 'Saved · untested' : 'Not configured'; badge.classList.toggle('saved', saved);
    $(`[data-remove="${input.dataset.secret}"]`).hidden = !saved;
  }
  $('#topic-button').textContent = next.has_topic ? 'Show subscription details' : 'Create my subscription';
  const labels = {untested: 'Not tested', sent: 'Sent · confirm phone receipt', confirmed: 'Phone delivery confirmed', failed: 'Needs attention · test failed'};
  $('#ntfy-status').textContent = next.choices.NOTIFICATIONS === 'skip' ? 'Deferred' : (next.has_topic ? labels[next.notification] : 'Not configured');
  $('#ntfy-status').classList.toggle('saved', next.notification === 'confirmed');
  $('#confirm-ntfy').disabled = !['sent', 'confirmed'].includes(next.notification);
  const providerKeys = ['REPLICATE_API_TOKEN','OPENAI_API_KEY','GEMINI_API_KEY','ANTHROPIC_API_KEY','OPENROUTER_API_KEY'];
  const count = next.saved_keys.filter(k => providerKeys.includes(k)).length;
  $('#review-list').replaceChildren();
  for (const text of [
    `${count} AI provider${count === 1 ? '' : 's'} saved${count ? ' — access still needs verification' : ' — fine for a static website'}.`,
    `Laptop SSH: ${next.choices.SSH_PUBLIC_KEY ? 'key saved — administrator activation and laptop connection test pending' : 'no key supplied'}.`,
    `Notifications: ${$('#ntfy-status').textContent.toLowerCase()}.`,
    `Backups: ${next.choices.BACKUPS === 'b2' ? 'selected — agent configuration and restore test pending' : next.choices.BACKUPS === 'skip' ? 'explicitly deferred' : 'choose or defer before finishing'}.`,
  ]) { const li = document.createElement('li'); li.textContent = text; $('#review-list').append(li); }
  panels();
}
async function save() {
  const choices = Object.fromEntries($$('[data-choice]').map(input => [input.dataset.choice, input.value]));
  choices.RECOVERY_DETAILS_SAVED = $('#recovery').checked ? 'yes' : '';
  const updates = Object.fromEntries($$('[data-secret]').filter(input => input.value.trim()).map(input => [input.dataset.secret, input.dataset.secret === 'RESTIC_PASSWORD' ? input.value : input.value.trim()]));
  const next = await api('save', {choices, secrets: updates, remove: [...removed]});
  for (const input of $$('[data-secret]')) input.value = '';
  removed.clear(); dirty = false; render(next);
  $('#save-state').textContent = 'Saved on your VPS. API keys remain untested.';
  return next;
}
async function run(task) {
  if (busy) return;
  busy = true;
  const buttons = $$('button, input, select'); const old = buttons.map(b => b.disabled);
  buttons.forEach(b => { b.disabled = true; });
  try { await task(); } catch (error) { message(error.message || 'Could not reach the setup server.', true); }
  finally { buttons.forEach((b, i) => { b.disabled = old[i]; }); busy = false;
    if (state) $('#confirm-ntfy').disabled = !['sent', 'confirmed'].includes(state.notification);
  }
}
$('#unlock-button').addEventListener('click', () => run(async () => {
  token = $('#setup-code').value.trim();
  const next = await api('status');
  $('#setup-code').value = ''; $('#unlock').hidden = true; $('#workspace').hidden = false;
  $('#message').hidden = true; render(next);
}));
$('#setup-code').addEventListener('keydown', event => { if (event.key === 'Enter') $('#unlock-button').click(); });
$('#setup-form').addEventListener('input', () => { dirty = true; $('#save-state').textContent = 'You have unsaved changes.'; panels(); });
$('#setup-form').addEventListener('submit', event => { event.preventDefault(); run(async () => { await save(); message('Choices saved. No paid API requests were made.'); }); });
for (const button of $$('[data-remove]')) button.addEventListener('click', () => {
  const key = button.dataset.remove; removed.add(key); $(`[data-secret="${key}"]`).value = '';
  $(`[data-status="${key}"]`).textContent = 'Will be removed from setup when saved';
  dirty = true; $('#save-state').textContent = 'Unsaved removal. Existing installed credentials are not revoked.';
});
$('#topic-button').addEventListener('click', () => run(async () => {
  await save();
  const data = await api(state.has_topic ? 'subscription' : 'topic', {});
  $('#topic').value = data.topic; $('#subscription').hidden = false;
  render(await api('status'));
  message('Subscribe to this topic in your ntfy phone app, then send a test.');
}));
$('#copy-topic').addEventListener('click', () => run(async () => {
  try { await navigator.clipboard.writeText($('#topic').value); message('Topic copied. Keep it private.'); }
  catch { $('#topic').focus(); $('#topic').select(); message('Select and copy the topic above.'); }
}));
$('#test-ntfy').addEventListener('click', () => run(async () => { await save(); render(await api('test-ntfy', {})); message('Test sent. Confirm here after it arrives on your phone.'); }));
$('#confirm-ntfy').addEventListener('click', () => run(async () => { render(await api('confirm-ntfy', {}), false); message('Phone delivery confirmed.'); }));
$('#finish-button').addEventListener('click', () => run(async () => {
  await save(); await api('finish', {}); token = ''; dirty = false;
  $('#workspace').hidden = true; $('#done').hidden = false; $('#subscription').hidden = true; $('#topic').value = '';
  $('#message').hidden = true; window.scrollTo(0, 0);
}));
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
