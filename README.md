# Carson Brantley — website

Bronx investment sales site for Carson Brantley, Alpha Capital Realty. Live rates that update themselves, a monthly market review and a blog.

## What's here

| File | What it is |
| --- | --- |
| `index.html` | Home page |
| `market.html` | Rates page: six rates, weekly recap, chart since 2021 |
| `reviews.html` | List of every monthly review |
| `reviews/` | One page per monthly review |
| `blog.html` | List of every blog post |
| `blog/` | One page per blog post (made by `scripts/new_post.py`) |
| `data/rates.json` | The rates. Updated automatically, never by hand |
| `data/reviews.json` | The list of reviews shown on the site |
| `data/posts.json` | The list of blog posts shown on the site |
| `assets/` | Styles, script, Alpha logo |
| `scripts/update_rates.py` | Pulls the latest rates from FRED |
| `scripts/new_post.py` | Turns a blog draft into a post page |
| `.github/workflows/site.yml` | Runs the update every weekday and publishes the site |

## How the rates update

Every weekday, around 8–9 AM and 5–6 PM New York time, GitHub runs `scripts/update_rates.py`. It downloads the latest readings from FRED (Federal Reserve Bank of St. Louis), saves them to `data/rates.json` and republishes the site. Nothing to do on your end.

To refresh right now: open the **Actions** tab, pick **Update rates and publish**, and press **Run workflow**.

Rates tracked (FRED series): Fed funds target (DFEDTARL, DFEDTARU), prime (DPRIME), SOFR (SOFR), 5-year Treasury (DGS5), 10-year Treasury (DGS10), 30-year mortgage (MORTGAGE30US).

## Adding a monthly review

1. Copy `reviews/2026-11-development-financing.html`, rename it for the new month (for example `reviews/2026-12-your-topic.html`) and replace the title and text.
2. Add the new review to the **top** of `data/reviews.json`. The newest entry shows on the home page and the rates page.

Or send the write-up to Claude and ask for it to be added.

## Adding a blog post

Send Claude the draft (from Perplexity or anywhere) and ask for it to be added. Claude saves it as a Markdown file with a short header, outside this folder, and runs:

    python3 scripts/new_post.py path/to/draft.md

That builds the post page in `blog/` in the site's layout, with the takeaway box up top, citation numbers that link to the Sources list, and the Sources list itself. It also puts the post at the top of `data/posts.json`. The newest three posts show on the home page.

The script stops without changing anything if the draft still has a `[VERIFY]` mark, has no Sources section, or cites a source number the list doesn't have. To fix a post that's already up, edit the draft and run it again with `--replace`.

The header at the top of the draft:

    ---
    title: Headline with a number in it
    summary: One or two sentences for the blog list and link previews.
    takeaway: The two-sentence takeaway that opens the post.
    date: 2026-11-08
    category: Development sites
    ---

Until the first post is up, the Blog page says the first post is coming soon and the home page doesn't show a blog section.

## Turning the site on (one time)

1. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push any change (or run the workflow). The site goes live at the address shown on that Settings page.
3. Custom domain: enter it on the same Pages settings page, then add the DNS records GitHub lists at the company you bought the domain from.

## Before sharing it

- Get sign-off from Alpha Capital Realty. New York requires the supervising broker to authorize an agent's website.
