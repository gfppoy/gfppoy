/* Email is stored in a Worker secret, never in the static site or repository. */
const SITEVERIFY = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
const ACTION = 'email-reveal';
const EMAIL = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/;

async function readBody(request) {
  if (!request.body) throw new Error('body');
  const reader = request.body.getReader(), decoder = new TextDecoder();
  let size = 0, text = '';
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 4096) { await reader.cancel(); throw new Error('size'); }
      text += decoder.decode(value, { stream: true });
    }
    return JSON.parse(text + decoder.decode());
  } finally { reader.releaseLock(); }
}

export function createHandler(verifyFetch = fetch) {
  return {
    async fetch(request, env) {
      const origin = request.headers.get('Origin');
      const allowed = (env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean);
      const trusted = allowed.includes(origin);
      const headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
        'Vary': 'Origin',
        'X-Content-Type-Options': 'nosniff',
        ...(trusted ? { 'Access-Control-Allow-Origin': origin } : {})
      };
      const reply = (status, body) => new Response(JSON.stringify(body), { status, headers });
      if (new URL(request.url).pathname !== '/reveal-email') return reply(404, { error: 'not_found' });
      if (!trusted) return reply(403, { error: 'forbidden' });
      if (request.method === 'OPTIONS') {
        return new Response(null, { status: 204, headers: { ...headers,
          'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' } });
      }
      if (request.method !== 'POST') return reply(405, { error: 'method_not_allowed' });
      if (!env.TURNSTILE_SECRET_KEY || !EMAIL.test(env.CONTACT_EMAIL || '')) return reply(503, { error: 'unavailable' });
      if (request.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/json') return reply(415, { error: 'invalid_request' });
      let body;
      try { body = await readBody(request); }
      catch (e) { return reply(e.message === 'size' ? 413 : 400, { error: 'invalid_request' }); }
      const token = body?.token;
      if (typeof token !== 'string' || !token.trim() || token.length > 2048) return reply(400, { error: 'invalid_request' });
      try {
        const response = await verifyFetch(SITEVERIFY, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ secret: env.TURNSTILE_SECRET_KEY, response: token,
            remoteip: request.headers.get('CF-Connecting-IP') || undefined }),
          signal: AbortSignal.timeout(8000)
        });
        if (!response.ok) return reply(503, { error: 'unavailable' });
        const result = await response.json();
        // CORS alone is not authorization. The verified hostname and action
        // must belong to this exact reveal flow, not another Turnstile widget.
        const timestamp = Date.parse(result.challenge_ts);
        const age = Date.now() - timestamp;
        if (result.success !== true || result.hostname !== new URL(origin).hostname || result.action !== ACTION ||
            !Number.isFinite(timestamp) || age < -30000 || age > 300000) {
          return reply(403, { error: 'verification_failed' });
        }
        return reply(200, { email: env.CONTACT_EMAIL });
      } catch { return reply(503, { error: 'unavailable' }); }
    }
  };
}
export default createHandler();
