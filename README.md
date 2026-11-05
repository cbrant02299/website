# Carson Brantley — website

Bronx investment sales site for Carson Brantley, Alpha Capital Realty. Live rates that update themselves, plus a monthly market review.

## What's here

| File | What it is |
| --- | --- |
| `index.html` | Home page |
| `market.html` | Rates page: six rates, weekly recap, chart since 2021 |
| `reviews.html` | List of every monthly review |
| `reviews/` | One page per monthly review |
| `data/rates.json` | The rates. Updated automatically, never by hand |
| `data/reviews.json` | The list of reviews shown on the site |
| `assets/` | Styles, script, Alpha logo |
| `scripts/update_rates.py` | Pulls the latest rates from FRED |
| `.github/workflows/site.yml` | Runs the update every weekday and publishes the site |

## How the rates update

Every weekday, around 8–9 AM and 5–6 PM New York time, GitHub runs `scripts/update_rates.py`. It downloads the latest readings from FRED (Federal Reserve Bank of St. Louis), saves them to `data/rates.json` and republishes the site. Nothing to do on your end.

To refresh right now: open the **Actions** tab, pick **Update rates and publish**, and press **Run workflow**.

Rates tracked (FRED series): Fed funds target (DFEDTARL, DFEDTARU), prime (DPRIME), SOFR (SOFR), 5-year Treasury (DGS5), 10-year Treasury (DGS10), 30-year mortgage (MORTGAGE30US).

## Adding a monthly review

1. Copy `reviews/2026-11-development-financing.html`, rename it for the new month (for example `reviews/2026-12-your-topic.html`) and replace the title and text.
2. Add the new review to the **top** of `data/reviews.json`. The newest entry shows on the home page and the rates page.

Or send the write-up to Claude and ask for it to be added.

## Turning the site on (one time)

1. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push any change (or run the workflow). The site goes live at the address shown on that Settings page.
3. Custom domain: enter it on the same Pages settings page, then add the DNS records GitHub lists at the company you bought the domain from.

## Before sharing it

- Replace `[Your license type]` in each page's footer with the license you hold.
- Get sign-off from Alpha Capital Realty. New York requires the supervising broker to authorize an agent's website.
