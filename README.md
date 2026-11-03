# Oregon Drug Help

Source for https://oregondrughelp.com, hosted on GitHub Pages.

- Page content lives in `src/pages/*.html` (a JSON block with title, description, quick answer, FAQ and sources, then the page HTML).
- Site-wide facts and the "last reviewed" date live in `src/site.json`.
- Run `python3 build.py` to regenerate every page, plus `sitemap.xml`, `robots.txt`, `llms.txt` and `llms-full.txt`.
- Commit the generated files; GitHub Pages serves them as-is (`.nojekyll`).
