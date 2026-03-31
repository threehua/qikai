# Furtune Family — furtune.org

Static website for [furtune.org](https://furtune.org) — the home of the Furtune Family and Rumi's Studio Journal.

## Pages

| File | Description |
|------|-------------|
| `index.html` | Home — origin story of the Furtune Family, told by Rumi |
| `journal.html` | Rumi's Studio Journal — release post listing |
| `posts/*.html` | Static HTML page per release post (SEO-friendly, fully crawlable) |
| `posts/*.md` | Source markdown for each post |

## Running locally

```bash
npx serve .
# → http://localhost:3000
```

## Structure

```
.
├── index.html              # Home / Our Story
├── journal.html            # Blog listing
├── style.css
├── marked.min.js           # Markdown renderer (vendored, used by journal listing)
├── favicon.ico
├── logo-icon.png
├── robots.txt
├── sitemap.xml
├── cats/                   # Cat illustrations
│   ├── fable.png
│   ├── rumi.png
│   └── unknown.png
├── posts/                  # One .md + .html pair per release
│   ├── 2026-02-23-v0.1.0.md
│   ├── 2026-02-23-v0.1.0.html
│   └── ...
└── .github/
    ├── workflows/
    │   └── auto-blog.yml   # Triggers on new release → generates post → pushes to main
    └── scripts/
        └── generate_post.py
```

## Auto-blog

New posts are generated automatically when a release is published. The workflow:

1. Triggered via `repository_dispatch` event (`new-furtune-release`)
2. Calls the Furtune API to generate a Rumi-voiced post from the release notes and PR descriptions
3. Writes `posts/{slug}.md` and `posts/{slug}.html`
4. Updates the `POSTS` array in `journal.html` and regenerates `sitemap.xml`
5. Commits and pushes directly to `main`

### Required secrets & variables

| Name | Type | Description |
|------|------|-------------|
| `NOVA_KEY` | Secret | Furtune API key |
| `FURTUNE_URL` | Secret | Furtune API base URL |
| `GH_TOKEN` | Secret | GitHub PAT with read access to the source repo |
| `NOVA_MODEL` | Variable | Agent slug to use (e.g. `nova-mini`) |
| `SOURCE_REPO` | Variable | Source repo in `owner/repo` format |

## Adding a post manually

1. Create `posts/YYYY-MM-DD-vX.Y.Z.md` with the post content
2. Run `python .github/scripts/generate_post.py` (with env vars set) — or manually create the matching `.html` using the same template structure
3. Add an entry to the `POSTS` array in `journal.html`
4. Commit and push — GitHub Pages deploys automatically

## Deployment

Hosted on [GitHub Pages](https://pages.github.com). Enable under **Settings → Pages → Deploy from branch `main`**.

Custom domain: `furtune.org`

---

*Part of the [Furtune Family](https://furtune.app) universe.*
