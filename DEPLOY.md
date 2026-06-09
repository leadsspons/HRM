# HRM Completion Dashboard Challenge

Telegram tasks -> Google Sheets (HRM) -> live PHP dashboards, with a Stripe
subscription front-end. Branded **Workidoki**.

Live site: https://saddlebrown-heron-782814.hostingersite.com/

## Repository layout
- `web/`  — the deployable PHP site (this is what runs on Hostinger / `public_html`)
- `bot.py`, `hrm.py`, `points.py`, `completion.py`, `config.py`, `seed.py` — the Telegram bot that feeds the Google Sheet
- `*.md` — schema, scoring and setup docs
- `hrm_data.xlsx` — sample seed data (the structure mirrored in the live Google Sheet)

## Continuous deployment (GitHub -> Hostinger)
Every push to `main` runs `.github/workflows/deploy.yml`, which FTP-uploads the
contents of `web/` to `public_html` on Hostinger.

### One-time setup — add 3 repository secrets
In GitHub: **Settings -> Secrets and variables -> Actions -> New repository secret**

| Secret name   | Where to find it (Hostinger hPanel) |
|---------------|--------------------------------------|
| `FTP_SERVER`   | Files -> FTP Accounts -> *FTP IP / hostname* (e.g. `ftp://82.x.x.x`) |
| `FTP_USERNAME` | Files -> FTP Accounts -> *Username* |
| `FTP_PASSWORD` | the password you set for that FTP account |

After the secrets are saved, push any change (or use the **Actions** tab ->
*Deploy to Hostinger* -> *Run workflow*) and the site updates automatically.

> The workflow **excludes** `config.php`, `service_account.json` and `data/` so
> your live sheet ID / Stripe keys on the server are never overwritten by a deploy.
> Edit those directly on the server (File Manager) when needed.

## Connecting real data
`web/config.php` points at a Google Sheet (gviz mode). The sheet must be shared
**Anyone with the link -> Viewer** for the site to read it. The bot (`bot.py`)
writes rows into that same sheet when run on a host/VPS.
