#!/usr/bin/env python3
"""Build the Oregon Drug Help website.

Each page lives in src/pages/<name>.html: a JSON block between `---json` and `---`,
then the page body HTML. Running `python3 build.py` writes:
  - every page as <path>/index.html (clean URLs)
  - sitemap.xml, robots.txt, llms.txt, llms-full.txt, 404.html
Structured data (JSON-LD), FAQ sections, sources and "last reviewed" dates are
generated from each page's JSON block so the visible page and the machine-readable
data never drift apart.
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "pages"
BASE = "https://oregondrughelp.com"
NAME = "Oregon Drug Help"
TAGLINE = "Free, plain-language help for drug and alcohol use in Oregon."

NAV = [
    ("/", "Home"),
    ("/free-treatment/", "Free treatment"),
    ("/find-help-by-county/", "Help by county"),
    ("/overdose/", "Overdose & naloxone"),
    ("/about/", "About"),
]

LOGO_SVG = (
    '<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false">'
    '<circle cx="16" cy="15" r="7" fill="var(--sun)"/>'
    '<path d="M0 22c6-4 11-4 16-1s10 2 16-1v12H0z" fill="var(--hill2)"/>'
    '<path d="M0 27c7-3 13-1 18 0s9 0 14-2v7H0z" fill="var(--hill3)"/></svg>'
)


def load_pages():
    pages = []
    for f in sorted(SRC.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---json\n(.*?)\n---\n(.*)", text, re.S)
        if not m:
            raise SystemExit(f"{f}: missing ---json front block")
        meta = json.loads(m.group(1))
        meta["body"] = m.group(2)
        meta["src"] = f.name
        pages.append(meta)
    pages.sort(key=lambda p: p.get("order", 99))
    return pages


def esc(s):
    return html.escape(s, quote=True)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def json_ld(page, reviewed):
    url = BASE + page["path"]
    org = {
        "@type": "Organization",
        "@id": BASE + "/#org",
        "name": NAME,
        "url": BASE + "/",
        "logo": BASE + "/assets/icon-512.png",
        "description": TAGLINE,
        "areaServed": {"@type": "State", "name": "Oregon"},
    }
    site = {
        "@type": "WebSite",
        "@id": BASE + "/#website",
        "name": NAME,
        "url": BASE + "/",
        "description": TAGLINE,
        "inLanguage": "en-US",
        "publisher": {"@id": BASE + "/#org"},
    }
    webpage = {
        "@type": page.get("schema_type", "MedicalWebPage"),
        "@id": url + "#webpage",
        "url": url,
        "name": page["title"],
        "headline": page["h1"],
        "description": page["description"],
        "inLanguage": "en-US",
        "isPartOf": {"@id": BASE + "/#website"},
        "publisher": {"@id": BASE + "/#org"},
        "lastReviewed": reviewed,
        "dateModified": reviewed,
        "spatialCoverage": {
            "@type": "State",
            "name": "Oregon",
            "containedInPlace": {"@type": "Country", "name": "United States"},
        },
        "primaryImageOfPage": BASE + "/assets/og-image.png",
    }
    if page.get("about"):
        webpage["about"] = page["about"]
    if page.get("audience"):
        webpage["audience"] = page["audience"]
    if page.get("answer"):
        webpage["abstract"] = " ".join(strip_tags(a) for a in page["answer"])
    if page.get("sources"):
        webpage["citation"] = [
            {"@type": "CreativeWork", "name": label, "url": link}
            for label, link in page["sources"]
        ]
    graph = [org, site, webpage]
    if page["path"] != "/":
        webpage["breadcrumb"] = {"@id": url + "#breadcrumb"}
        graph.append({
            "@type": "BreadcrumbList",
            "@id": url + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": page["crumb"], "item": url},
            ],
        })
    if page.get("faq"):
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "isPartOf": {"@id": url + "#webpage"},
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)},
                }
                for q, a in page["faq"]
            ],
        })
    if page.get("howto"):
        h = page["howto"]
        graph.append({
            "@type": "HowTo",
            "@id": url + "#howto",
            "name": h["name"],
            "description": h.get("description", ""),
            "step": [
                {"@type": "HowToStep", "position": i + 1, "name": s[0], "text": s[1]}
                for i, s in enumerate(h["steps"])
            ],
        })
    if page.get("extra_ld"):
        graph.extend(page["extra_ld"])
    data = {"@context": "https://schema.org", "@graph": graph}
    return json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")


def head(page, reviewed):
    url = BASE + page["path"]
    # Keep titles short enough for search results; add the site name only when there's room.
    title = page["title"]
    if page["path"] != "/" and len(title) <= 42:
        title = f"{title} | {NAME}"
    return f"""<!DOCTYPE html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(page['description'])}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{'noindex, follow' if page.get('noindex') else 'index, follow, max-snippet:-1, max-image-preview:large'}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{esc(page['title'])}">
<meta property="og:description" content="{esc(page['description'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#3F7F7B">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/icon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/assets/icon-180.png">
<link rel="alternate" type="text/plain" title="LLM summary" href="/llms.txt">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500&amp;family=Figtree:wght@400;500;600&amp;display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
<script type="application/ld+json">
{json_ld(page, reviewed)}
</script>
</head>
"""


def top(page):
    items = []
    for path, label in NAV:
        cur = ' aria-current="page"' if path == page["path"] else ""
        items.append(f'<li><a href="{path}"{cur}>{esc(label)}</a></li>')
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<div class="crisis">
  <div class="wrap">
    <span>In crisis? Call or text <a href="tel:988">988</a>.</span>
    <span>Someone not breathing? Call <a href="tel:911">911</a>.</span>
    <span>Oregon Alcohol &amp; Drug Helpline: <a href="tel:18009234357">1-800-923-4357</a>, 24/7.</span>
  </div>
</div>
<nav class="site-nav" aria-label="Main">
  <div class="wrap">
    <a class="brand" href="/">{LOGO_SVG}<span>{NAME}</span></a>
    <ul>
      {chr(10).join('      ' + i for i in items).strip()}
    </ul>
  </div>
</nav>
"""


def human_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")


def page_head(page, reviewed):
    if page["path"] == "/":
        return ""
    return f"""<header class="page-head">
  <div class="wrap">
    <nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="/">Home</a></li><li aria-current="page">{esc(page['crumb'])}</li></ol></nav>
    <h1>{page['h1']}</h1>
    <p class="lead">{page['lead']}</p>
    <p class="reviewed">Last reviewed <time datetime="{reviewed}">{human_date(reviewed)}</time> · Sources listed at the bottom of this page</p>
  </div>
</header>
"""


def answer_box(page):
    if not page.get("answer"):
        return ""
    lis = "\n".join(f"        <li>{a}</li>" for a in page["answer"])
    return f"""<section class="tight" aria-labelledby="quick-answer">
  <div class="wrap">
    <div class="answer">
      <h2 id="quick-answer">{esc(page.get('answer_title', 'The short answer'))}</h2>
      <ul>
{lis}
      </ul>
    </div>
  </div>
</section>
"""


def faq_section(page):
    if not page.get("faq"):
        return ""
    items = "\n".join(
        f"      <details><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in page["faq"]
    )
    cls = page.get("faq_class", "")
    return f"""<section id="faq" class="{cls}" aria-labelledby="faq-title">
  <div class="wrap">
    <div class="intro"><h2 id="faq-title">Common questions</h2></div>
    <div class="faq">
{items}
    </div>
  </div>
</section>
"""


def sources_section(page, reviewed):
    if not page.get("sources"):
        return ""
    lis = "\n".join(
        f'        <li><a href="{esc(u)}">{esc(l)}</a></li>' for l, u in page["sources"]
    )
    return f"""<section class="tight" aria-labelledby="sources-title" style="padding-bottom:4rem">
  <div class="wrap">
    <div class="sources">
      <h2 id="sources-title">Sources</h2>
      <p>Last reviewed <time datetime="{reviewed}">{human_date(reviewed)}</time>. Services and phone numbers can change, so check with each provider.</p>
      <ol>
{lis}
      </ol>
    </div>
  </div>
</section>
"""


def footer():
    links = "".join(f'<li><a href="{p}">{esc(l)}</a></li>' for p, l in NAV)
    return f"""<footer>
  <div class="wrap">
    <nav aria-label="Footer"><ul>{links}</ul></nav>
    <p>{NAME} shares general information and isn’t a substitute for medical or legal advice. If you or someone else is in immediate danger, call 911.</p>
    <p>We are an independent site and are not affiliated with any agency, treatment center or program listed.</p>
  </div>
</footer>
</body>
</html>
"""


class TextOut(HTMLParser):
    """Turn rendered page HTML into readable plain text for llms-full.txt."""
    BLOCK = {"p", "li", "h1", "h2", "h3", "dt", "dd", "summary", "tr", "br", "section", "div"}

    def __init__(self):
        super().__init__()
        self.out, self.skip, self.href = [], 0, None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "nav"):
            self.skip += 1
        if tag in ("h1", "h2", "h3"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in self.BLOCK:
            self.out.append("\n")
        if tag == "a":
            self.href = dict(attrs).get("href")
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "nav"):
            self.skip -= 1
        if tag == "a" and self.href and self.href.startswith("http") and not self.skip:
            self.out.append(f" ({self.href})")
            self.href = None

    def handle_data(self, data):
        if not self.skip:
            self.out.append(re.sub(r"\s+", " ", data))

    def text(self):
        t = "".join(self.out)
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n[ \t]+", "\n", t)
        return re.sub(r"\n{3,}", "\n\n", t).strip()


def main():
    pages = load_pages()
    reviewed_default = json.loads((ROOT / "src" / "site.json").read_text())["reviewed"]
    llms_full = []
    for p in pages:
        reviewed = p.get("reviewed", reviewed_default)
        main_html = (
            page_head(p, reviewed)
            + '<main id="main">\n'
            + answer_box(p)
            + p["body"]
            + faq_section(p)
            + sources_section(p, reviewed)
            + "</main>\n"
        )
        doc = head(p, reviewed) + top(p) + main_html + footer()
        if p.get("out_file"):
            out = ROOT / p["out_file"]
        elif p["path"] == "/":
            out = ROOT / "index.html"
        else:
            out = ROOT / p["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        if p.get("in_sitemap", True):
            t = TextOut()
            t.feed(main_html)
            llms_full.append(
                f"# {p['title']}\nURL: {BASE}{p['path']}\nLast reviewed: {reviewed}\n\n{t.text()}"
            )
        p["_reviewed"] = reviewed
        print("wrote", out.relative_to(ROOT))

    listed = [p for p in pages if p.get("in_sitemap", True)]

    # sitemap.xml
    urls = "\n".join(
        f"  <url><loc>{BASE}{p['path']}</loc><lastmod>{p['_reviewed']}</lastmod></url>" for p in listed
    )
    (ROOT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
    )

    # llms.txt (https://llmstxt.org) — a short, factual map of the site for AI agents
    home = next(p for p in pages if p["path"] == "/")
    lines = [
        f"# {NAME}",
        "",
        f"> {TAGLINE} An independent, statewide guide to helplines, free and low-cost treatment, "
        "overdose response and naloxone, and help in every county. Not affiliated with any treatment center.",
        "",
        "## Key facts (Oregon)",
        "",
    ]
    lines += [f"- {strip_tags(f)}" for f in json.loads((ROOT / "src" / "site.json").read_text())["key_facts"]]
    lines += ["", "## Pages", ""]
    for p in listed:
        lines.append(f"- [{p['title']}]({BASE}{p['path']}): {p['description']}")
    lines += [
        "",
        "## Optional",
        "",
        f"- [Full text of every page]({BASE}/llms-full.txt): plain-text version of the whole site for AI tools.",
        f"- [Sitemap]({BASE}/sitemap.xml)",
        "",
        f"Last reviewed: {reviewed_default}. This site gives general information, not medical or legal advice. "
        "In an emergency call 911.",
        "",
    ]
    (ROOT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "llms-full.txt").write_text(
        f"# {NAME} — full text\n\n> {TAGLINE}\n\n" + "\n\n---\n\n".join(llms_full) + "\n", encoding="utf-8"
    )
    # robots.txt — welcome search engines and AI search/answer crawlers alike
    bots = [
        "Googlebot", "Bingbot", "Google-Extended", "GPTBot", "OAI-SearchBot", "ChatGPT-User",
        "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User",
        "Applebot", "Applebot-Extended", "DuckAssistBot", "CCBot",
    ]
    robots = ["# Oregon Drug Help welcomes search engines and AI assistants.", ""]
    for b in bots:
        robots += [f"User-agent: {b}", "Allow: /", ""]
    robots += ["User-agent: *", "Allow: /", "", f"Sitemap: {BASE}/sitemap.xml", ""]
    (ROOT / "robots.txt").write_text("\n".join(robots))
    print("wrote sitemap.xml, robots.txt, llms.txt, llms-full.txt")


if __name__ == "__main__":
    main()
