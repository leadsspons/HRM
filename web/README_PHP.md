# Emirard HRM — PHP Web Service (`web/`)

Drop this folder into your PHP web server (Apache/Nginx + PHP 7.4+). It serves the
service landing page, the dashboards, and a JSON API backed by your Google Sheet.

```
web/
├─ index.php          Service landing page (links + live status)
├─ api.php            JSON API (reads + optional writes)
├─ config.php         Sheet ID, mode, credentials, write key
├─ lib/Sheets.php     Google Sheets layer (Sheets API or gviz)
├─ .htaccess          Default doc + protects config/keys
├─ dashboard.html     🏆 Challenge Leaderboard
├─ employee_tracker.html  📋 Employee Tracker (manager)
├─ user_challenge.html    🔥 Team Challenge (staff)
├─ admin.html         ⚙️ Admin Console
└─ guide_en/ko.html   📘 Setup guides
```

## 1. Deploy
Copy `web/` under your document root (e.g. `/var/www/html/hrm`). Requires PHP with
`openssl` and either `curl` or `allow_url_fopen` (both standard).

## 2. Configure (`config.php`)
| key | meaning |
|---|---|
| `sheet_id` | Google Sheet ID (the `/d/<ID>/edit` part) |
| `mode` | `auto` (default) · `api` (private, read+write) · `gviz` (published, read-only) |
| `sa_keyfile` | path to `service_account.json` (for `api` mode) |
| `cache_ttl` | seconds to cache reads (default 30) |
| `write_key` | shared secret to allow web writes; empty = writes disabled |

You can also set these via environment variables: `HRM_SHEET_ID`, `HRM_MODE`,
`GOOGLE_SA_KEYFILE`, `HRM_WRITE_KEY`.

### Two data modes
- **gviz (easiest, read-only)** — In the Sheet: *File → Share → Publish to web*.
  Set `mode='gviz'`. No credentials needed. Dashboards go live immediately.
- **Sheets API (private sheet, read + write)** — Put the bot's `service_account.json`
  next to `config.php`, share the Sheet with the service-account email as Editor,
  set `mode='api'`. This also enables the Admin Console write endpoints.

## 3. JSON API
```
GET  api.php?action=health
     → {"ok":true,"mode":"api","sheet_configured":true}
GET  api.php?action=rows&tab=Quarter
     → {"ok":true,"tab":"Quarter","count":7,"rows":[{...}]}
     tabs: Tasks · Members · Groups · Points · Quarter · Activity · Votes
POST api.php?action=register_group&key=YOUR_WRITE_KEY
     body: {"name":"Growth Room","invite_url":"https://t.me/+..","bot_token":""}
POST api.php?action=register_member&key=YOUR_WRITE_KEY
     body: {"username":"sara_k","display_name":"Sara Kim","team":"Growth"}
```
Writes require `mode='api'` and a matching `write_key`.

## 4. How the dashboards find data
Each dashboard tries, in order:
1. `api.php?action=rows&tab=…` (same origin — works when served here)
2. `CONFIG.sheetId` + Google gviz (if you hardcoded a sheet id in the file)
3. Built-in sample data (so it always renders)

So once `web/` is served by PHP with a configured sheet, all dashboards are live —
no per-file editing needed.

## 5. Security notes
- `.htaccess` denies direct access to `config.php`, `service_account.json`, `seed.json`.
  On Nginx, add equivalent `location` deny rules.
- Keep `write_key` secret; without it the API is read-only.
- Serve over HTTPS in production.

## 6. Subscriptions (Stripe)
The site includes a subscription paywall so any company can subscribe.

**Files:** `pricing.php` (3 plans), `subscribe.php` (creates Checkout Session),
`success.php`, `webhook.php`, `lib/Stripe.php`.

**Setup:**
1. Create a Stripe account → Dashboard → Developers → API keys. Copy the **secret**
   and **publishable** keys into `config.php` (`stripe.secret_key`, `publishable_key`).
2. Dashboard → Products → create 3 **recurring (monthly)** prices (Starter/Pro/Enterprise),
   copy each `price_…` ID into `config.php` (`stripe.prices`).
3. Set `stripe.site_url` to your public URL (e.g. `https://yourdomain.com`).
4. Dashboard → Developers → Webhooks → add endpoint `https://YOUR-SITE/webhook.php`,
   subscribe to `checkout.session.completed` and `customer.subscription.*`,
   copy the signing secret (`whsec_…`) into `config.php` (`stripe.webhook_secret`).

All keys can also be set as environment variables (`STRIPE_SECRET_KEY`,
`STRIPE_PRICE_PRO`, etc.) instead of editing `config.php`.

**Default plans** (edit in `pricing.php`): Starter $29 · Pro $79 · Enterprise $199 /mo.

**Security:** never commit live secret keys; `.htaccess` blocks `config.php` and the
`data/` folder (where webhook records subscribers). Always serve over HTTPS.
