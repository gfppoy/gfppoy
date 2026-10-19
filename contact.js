/* The address is fetched only after server-verified Turnstile success. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const trigger = $('contact-email'), panel = $('contact-panel');
  if (!trigger || !panel) return;
  const config = window.contactConfig || {};
  const status = $('contact-status'), challenge = $('contact-challenge'), retry = $('contact-retry');
  let widget = null, generation = 0, request = null, scriptPromise = null, address = '';
  function configured() {
    try { return !!config.siteKey && new URL(config.endpoint).protocol === 'https:'; }
    catch { return false; }
  }
  function loadTurnstile() {
    if (window.turnstile) return Promise.resolve();
    if (scriptPromise) return scriptPromise;
    scriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      let timeout;
      const fail = () => { clearTimeout(timeout); script.remove(); reject(new Error('load')); };
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.onload = () => { clearTimeout(timeout); window.turnstile ? resolve() : fail(); };
      script.onerror = fail;
      timeout = setTimeout(fail, 12000);
      document.head.appendChild(script);
    }).catch(error => { scriptPromise = null; throw error; });
    return scriptPromise;
  }
  function clearWidget() {
    if (widget !== null && window.turnstile) window.turnstile.remove(widget);
    widget = null; challenge.replaceChildren();
  }
  function clearAddress() {
    address = ''; $('contact-address').value = ''; $('contact-open').removeAttribute('href');
    $('contact-result').hidden = true; $('contact-copy').textContent = 'Copy address';
  }
  function fail(message, id) {
    if (generation !== id || panel.hidden) return;
    status.textContent = message; retry.hidden = false;
  }
  async function verify(token, id) {
    if (generation !== id || panel.hidden) return;
    request?.abort(); request = new AbortController();
    const controller = request, timeout = setTimeout(() => controller.abort(), 12000);
    status.textContent = 'Verifying…';
    try {
      const response = await fetch(config.endpoint, { method: 'POST', mode: 'cors', credentials: 'omit', cache: 'no-store',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token }), signal: controller.signal });
      if (!response.ok) throw new Error('verification');
      const data = await response.json();
      if (typeof data.email !== 'string' || !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(data.email)) throw new Error('response');
      if (generation !== id || panel.hidden) return;
      address = data.email; clearWidget();
      $('contact-address').value = address; $('contact-open').href = `mailto:${encodeURIComponent(address)}`;
      $('contact-intro').hidden = true; $('contact-result').hidden = false; retry.hidden = true;
      status.textContent = 'Address revealed.';
      $('contact-address').focus({ preventScroll: true }); $('contact-address').select();
    } catch { fail('Couldn’t verify. Please try again.', id); }
    finally { clearTimeout(timeout); }
  }
  async function start() {
    const id = ++generation;
    request?.abort(); clearWidget(); clearAddress(); retry.hidden = true; $('contact-intro').hidden = false;
    if (!configured()) { $('contact-intro').hidden = true; status.textContent = 'Email is not available yet.'; return; }
    status.textContent = 'Loading the check…';
    try {
      await loadTurnstile();
      if (generation !== id || panel.hidden) return;
      status.textContent = '';
      widget = window.turnstile.render(challenge, { sitekey: config.siteKey, action: 'email-reveal', theme: 'light',
        size: innerWidth < 420 ? 'compact' : 'normal', appearance: 'always', retry: 'never',
        callback: token => verify(token, id),
        'error-callback': () => { fail('The check couldn’t complete. Please try again.', id); return true; },
        'expired-callback': () => fail('The check expired. Please try again.', id),
        'timeout-callback': () => fail('The check timed out. Please try again.', id)
      });
    } catch { fail('The check couldn’t load. Please try again.', id); }
  }
  function close(restoreFocus = true) {
    if (panel.hidden) return;
    generation++; request?.abort(); clearWidget(); clearAddress();
    panel.hidden = true; trigger.setAttribute('aria-expanded', 'false');
    if (restoreFocus) trigger.focus({ preventScroll: true });
  }
  trigger.hidden = false;
  trigger.addEventListener('click', () => {
    if (!panel.hidden) { close(); return; }
    panel.hidden = false; trigger.setAttribute('aria-expanded', 'true');
    $('contact-close').focus({ preventScroll: true }); start();
  });
  $('contact-close').addEventListener('click', () => close());
  retry.addEventListener('click', start);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) { event.preventDefault(); close(); } });
  document.addEventListener('click', event => { if (!panel.hidden && !panel.contains(event.target) && !trigger.contains(event.target)) close(false); });
  $('contact-copy').addEventListener('click', async () => {
    if (!address) return;
    const id = generation;
    try { await navigator.clipboard.writeText(address); if (id === generation) status.textContent = 'Copied.'; }
    catch { if (id === generation) { $('contact-address').focus(); $('contact-address').select(); status.textContent = 'Select and copy the address above.'; } }
  });
})();
