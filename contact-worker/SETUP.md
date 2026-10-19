# Activate the email reveal

The frontend is configured for the deployed `darius-contact` Worker. No address is shipped to the browser as a fallback. The steps below document setup and future maintenance. Production must allow only `dariusmuglich.com` and `www.dariusmuglich.com`; remove local-development hostnames from Turnstile and local origins from the Worker dashboard.

Your domain stays with GoDaddy and the website stays on GitHub Pages. Only the small verification endpoint runs on Cloudflare. You do not need to change your nameservers or transfer the domain.

## Cost

Use **Turnstile Free** and **Workers Free**. This implementation needs no paid databases or other paid services. Workers Free currently includes 100,000 requests per day; exceeding the free request limit interrupts service rather than requiring this project to upgrade automatically. Keep the account on the Free plan.

- [Turnstile plans](https://developers.cloudflare.com/turnstile/plans/)
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)

## 1. Create the check

Create a free Cloudflare account, then open **Turnstile → Add widget**.

- Name: `Website email`.
- Hostnames: `dariusmuglich.com` and `www.dariusmuglich.com`.
- Mode: **Managed**.
- Pre-clearance is not needed.

Save the **site key** (public) and **secret key** (private). Never put the secret key in GitHub, HTML, JavaScript configuration, or chat.

If you first test on your GitHub Pages hostname, add that exact hostname to the widget as well. Hostnames contain no `https://` or path.

[Official widget setup](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/)

## 2. Create the small backend

In Cloudflare, open **Workers & Pages**, create a Worker named `darius-contact`, and use the dashboard code editor to replace the starter code with the complete contents of `worker.mjs`. This file is self-contained. Deploy it on the **Free** plan.

In the Worker's settings, add these variables/secrets:

| Name | Type | Value |
| --- | --- | --- |
| `TURNSTILE_SECRET_KEY` | Secret | The private key from step 1 |
| `CONTACT_EMAIL` | Secret | Your intended email address |
| `ALLOWED_ORIGINS` | Text | `https://dariusmuglich.com,https://www.dariusmuglich.com` |

Save/deploy the settings. The Worker refuses to reveal anything while the secrets are missing.

If testing on GitHub Pages before the custom domain is live, also add its exact origin to `ALLOWED_ORIGINS`, e.g. `https://gfppoy.github.io`. Origins include `https://` but no trailing slash or repository path. That hostname must also be allowed by the Turnstile widget.

Cloudflare gives the Worker a URL resembling `https://darius-contact.YOUR-SUBDOMAIN.workers.dev`. The endpoint is that URL followed by `/reveal-email`.

[Official Worker dashboard setup](https://developers.cloudflare.com/workers/get-started/dashboard/)

Optional CLI alternative, from this directory:

```sh
npx wrangler login
npx wrangler deploy
npx wrangler secret put TURNSTILE_SECRET_KEY
npx wrangler secret put CONTACT_EMAIL
```

The secret commands prompt privately; do not place secret values directly in command arguments. `wrangler.toml` contains the production origin list. If you edit origins through the dashboard, keep this file in sync before future CLI deployments.

## 3. Connect the website

In `../contact-config.js`, set:

```js
window.contactConfig = Object.freeze({
  siteKey: 'YOUR_PUBLIC_SITE_KEY',
  endpoint: 'https://darius-contact.YOUR-SUBDOMAIN.workers.dev/reveal-email'
});
```

Only these two values are public. There must be no actual email address or Turnstile secret in this file. Publish the updated static files to GitHub Pages using the site's normal deployment process.

## 4. Check the live flow

On an allowed HTTPS hostname:

1. Click Email. The check loads only after this click.
2. Complete it if prompted; the address, Copy address, and Open email actions appear.
3. Close the panel; the revealed address is cleared from this page's UI.
4. Test keyboard navigation, Escape, and a narrow mobile screen.
5. A POST with a fabricated token must be rejected. A GET request to the endpoint must not reveal the address.

Local automated tests mock Cloudflare responses and cover rejected, stale, replayed, wrong-host and wrong-action tokens. They do **not** substitute for this live check with real account keys.

## Security boundary

The server validates every token with Cloudflare, then checks the verified hostname and `email-reveal` action. The allowed-origin list is an additional restriction, not authentication by itself. Responses cannot be cached. Network failures fail closed, without exposing an address. No tokens or addresses are logged by the handler.

Anyone who successfully reveals the address can retain it. This does not remove addresses from previously published files, repository history, CVs, or other websites, and cannot prevent spam to an already-known address. JavaScript and access to Cloudflare's challenge service are required for this reveal flow.
