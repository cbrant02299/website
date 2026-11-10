#!/usr/bin/env python3
"""Turn a blog draft written in Markdown into a post on the site.

    python3 scripts/new_post.py path/to/draft.md             add a new post
    python3 scripts/new_post.py path/to/draft.md --replace   update a post that's already up

The draft opens with a short header, then the post in Markdown:

    ---
    title: Headline with a number in it
    summary: One or two sentences for the blog list and link previews.
    takeaway: The two-sentence takeaway that opens the post.
    date: 2026-11-08
    category: Development sites
    ---

    Paragraphs, ## section headings, lists, tables and links.
    Citation marks like [1] link to the matching line under "## Sources",
    which should be the last section.

It writes blog/<YYYY-MM>-<slug>.html in the site's layout and adds the post to
the top of data/posts.json, which feeds the Blog page and the home page.

It stops without writing anything if the draft still has a [VERIFY] mark, has
no Sources section, or cites a source number the Sources list doesn't have.

Needs the Markdown package (pip install markdown). The site itself doesn't:
this only runs when a post is added.
"""

import argparse
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from string import Template

try:
    import markdown
except ImportError:
    sys.exit("This script needs the Markdown package. Run: pip install markdown")

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "data" / "posts.json"
BLOG = ROOT / "blog"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fail(message):
    sys.exit("Stopped: " + message)


def read_draft(path):
    """Return (header fields, Markdown body)."""
    text = Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    fields, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---", 3)
        if end == -1:
            fail("the header at the top needs a closing --- line.")
        header = text[4:end]
        body = text[end + 4:].split("\n", 1)[1] if "\n" in text[end + 4:] else ""
        for line in header.split("\n"):
            if not line.strip():
                continue
            if ":" not in line:
                fail("this header line isn't in 'name: value' form: " + line)
            key, value = line.split(":", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            fields[key.strip().lower()] = value
    # A "# Headline" at the top of the body is the title; drop it so it isn't shown twice.
    m = re.match(r"\s*#\s+(.+?)\s*#*\s*(\n|$)", body)
    if m:
        if not fields.get("title"):
            fields["title"] = m.group(1)
        body = body[m.end():]
    return fields, body


def slugify(text):
    text = text.replace("&", " and ")
    text = re.sub(r"[‐-―]", "-", text)  # en and em dashes
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    if len(text) > 60:
        text = text[:60].rsplit("-", 1)[0]
    return text or "post"


def long_date(d):
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


CITE = re.compile(r"[ \t]*\[(\d{1,3}(?:\s*,\s*\d{1,3})*)\]")


def link_citations(fragment, count):
    """Turn [1], [1, 2] or [1][2] into small linked numbers that jump to the source."""
    def one(match):
        numbers = [int(n) for n in re.split(r"\s*,\s*", match.group(1))]
        for n in numbers:
            if n < 1 or n > count:
                fail(f"the draft cites [{n}], but the Sources list has {count} item(s).")
        links = ",".join(f'<a href="#source-{n}" aria-label="Source {n}">{n}</a>' for n in numbers)
        return f'<sup class="cite">{links}</sup>'
    return CITE.sub(one, fragment).replace('</sup><sup class="cite">', ",")


def build_body(md_body):
    """Markdown -> the article's HTML: (main text, Sources section)."""
    converted = markdown.markdown(md_body, extensions=["tables", "sane_lists"], output_format="html")

    m = re.search(r"<h[23][^>]*>\s*Sources:?\s*</h[23]>", converted, re.I)
    if not m:
        fail('the draft needs a "## Sources" section at the end that lists every source.')
    main, rest = converted[:m.start()], converted[m.end():]
    later = re.search(r"<h2[^>]*>", rest)
    sources, after = (rest[:later.start()], rest[later.start():]) if later else (rest, "")
    main += after

    # Sources are numbered so [1] in the text matches line 1.
    sources = re.sub(r"<ul>", "<ol>", sources, count=1)
    sources = re.sub(r"</ul>", "</ol>", sources, count=1)
    counter = iter(range(1, 1000))
    head, sep, tail = sources.partition("</ol>")
    head = re.sub(r"<li>", lambda _: f'<li id="source-{next(counter)}">', head)
    sources = head + sep + tail
    count = len(re.findall(r'<li id="source-', sources))
    if not count:
        fail("the Sources section needs a list, one source per line.")

    return main, sources, count


def finish(fragment):
    """Tables scroll sideways on phones; outside links open in a new tab."""
    fragment = fragment.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    return re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', fragment)


PAGE = Template("""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>$title_attr | Carson Brantley</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="$summary_attr">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Carson Brantley">
<meta property="og:title" content="$title_attr">
<meta property="og:description" content="$summary_attr">
<meta property="article:published_time" content="$date_iso">
<link rel="icon" href="../assets/alpha-emblem.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&amp;display=swap">
<link rel="stylesheet" href="../assets/site.css">
<script type="application/ld+json">
$ld_json
</script>
</head>
<body data-root="..">

<header class="site-header">
  <div class="wrap">
    <a class="brand" href="../index.html">
      <img src="../assets/alpha-emblem.png" alt="" width="44" height="44">
      <span><span class="brand-name">Carson Brantley</span><span class="brand-firm">Alpha Capital Realty</span></span>
    </a>
    <nav class="nav" aria-label="Main">
      <a href="../index.html">Home</a>
      <a href="../market.html">Rates</a>
      <a href="../reviews.html">Monthly Review</a>
      <a href="../blog.html" aria-current="page">Blog</a>
      <a href="../index.html#contact">Contact</a>
    </nav>
  </div>
</header>

<main>
  <article>
    <header class="page-head">
      <div class="wrap stack">
        <p class="eyebrow">$eyebrow</p>
        <h1 class="h-page">$title</h1>
        <p class="byline"><span>Carson Brantley</span><span>Alpha Capital Realty</span><span><time datetime="$date_iso">$date_long</time></span></p>
      </div>
    </header>

    <div class="wrap" style="padding-bottom: clamp(56px, 8vw, 96px)">
      <div class="article">
$takeaway
$main

        <section class="sources" aria-labelledby="sources-h">
          <h2 id="sources-h">Sources</h2>
$sources
        </section>

        <p class="fine">Numbers are as of $date_long and come from the sources above. This is general market information, not an appraisal or an offer to buy or sell property.</p>

        <div class="actions">
          <a class="btn btn-line" href="../blog.html">All posts</a>
          <a class="btn btn-gold" href="../market.html">Today's rates</a>
        </div>
      </div>
    </div>
  </article>
</main>

<footer class="site-footer">
  <div class="wrap">
    <img class="footer-logo" src="../assets/alpha-logo.png" alt="Alpha Capital" width="643" height="474">
    <div class="footer-body">
      <p class="footer-id">Carson Brantley, <span class="license">Licensed Real Estate Salesperson</span><br>Alpha Capital Realty · <a href="https://www.alphacapitalfunds.com" target="_blank" rel="noopener">alphacapitalfunds.com</a></p>
      <nav class="footer-nav" aria-label="Footer">
        <a href="../index.html">Home</a><a href="../market.html">Rates</a><a href="../reviews.html">Monthly Review</a><a href="../blog.html">Blog</a><a href="../index.html#contact">Contact</a>
      </nav>
      <p class="fine">Rates come from FRED, Federal Reserve Bank of St. Louis, and update every weekday. Everything on this site is general market information. It is not a loan quote, an appraisal or an offer to buy or sell property.</p>
      <p class="fine">© 2026 Carson Brantley</p>
    </div>
  </div>
</footer>

</body>
</html>
""")


def main():
    parser = argparse.ArgumentParser(description="Add a blog post to the site from a Markdown draft.")
    parser.add_argument("draft", help="the Markdown draft")
    parser.add_argument("--replace", action="store_true", help="overwrite a post that's already on the site")
    args = parser.parse_args()

    raw = Path(args.draft).read_text(encoding="utf-8")
    flagged = [line.strip() for line in raw.splitlines() if re.search(r"\[\s*verify\s*\]", line, re.I)]
    if flagged:
        fail("the draft still has numbers marked [VERIFY]. Confirm or cut them first:\n  " + "\n  ".join(flagged))

    fields, body = read_draft(args.draft)
    for key in ("title", "summary", "date"):
        if not fields.get(key):
            fail(f"the header at the top needs a {key}: line.")
    try:
        day = date.fromisoformat(fields["date"])
    except ValueError:
        fail("date must look like 2026-11-08.")
    title, summary = fields["title"], fields["summary"]
    category = fields.get("category", "")

    main_html, sources_html, count = build_body(body)
    main_html = finish(link_citations(main_html, count))
    sources_html = finish(sources_html)
    takeaway_html = ""
    if fields.get("takeaway"):
        inner = link_citations(markdown.markdown(fields["takeaway"]), count)
        takeaway_html = ('<aside class="takeaway" aria-label="The short version">\n'
                         '<span class="figure-title">The short version</span>\n' + finish(inner) + "\n</aside>")

    slug = slugify(fields.get("slug") or title)
    url = f"blog/{day:%Y-%m}-{slug}.html"
    out = ROOT / url
    if out.exists() and not args.replace:
        fail(f"{url} already exists. Add --replace to update it.")

    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": summary,
        "datePublished": day.isoformat(),
        "author": {"@type": "Person", "name": "Carson Brantley",
                   "worksFor": {"@type": "Organization", "name": "Alpha Capital Realty"}},
    }
    page = PAGE.substitute(
        title=html.escape(title, quote=False),
        title_attr=html.escape(title),
        summary_attr=html.escape(summary),
        eyebrow=html.escape("Blog · " + (category or f"{MONTHS[day.month - 1]} {day.year}"), quote=False),
        date_iso=day.isoformat(),
        date_long=long_date(day),
        ld_json=json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/"),
        takeaway=takeaway_html,
        main=main_html.strip(),
        sources=sources_html.strip(),
    )
    BLOG.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")

    posts = json.loads(POSTS.read_text(encoding="utf-8")) if POSTS.exists() else []
    posts = [p for p in posts if p.get("url") != url]
    entry = {"date": day.isoformat(), "title": title, "summary": summary, "url": url}
    if category:
        entry["category"] = category
    posts.insert(0, entry)
    posts.sort(key=lambda p: p.get("date", ""), reverse=True)  # newest first; same-day ties keep the new post on top
    POSTS.write_text(json.dumps(posts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{'Updated' if args.replace else 'Added'} {url}")
    print(f"data/posts.json now lists {len(posts)} post(s).")


if __name__ == "__main__":
    main()
