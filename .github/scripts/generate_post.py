"""
Generates a Rumi-voiced blog post for a new Furtune app release and
updates posts/ + journal.html accordingly.

Required env vars:
  NOVA_KEY      - furtune.app API key (Bearer token)
  FURTUNE_URL   - OpenAI-compatible base URL  (e.g. https://furtune.app/api/v1)
  NOVA_MODEL    - Agent slug to use            (e.g. nova-mini)
  GH_TOKEN      - GitHub PAT with read access to the source repo
  SOURCE_REPO   - GitHub repo in owner/repo format (set as a repo variable)
  VERSION       - Release tag, e.g. v0.7.0
  PUBLISHED_AT  - ISO 8601 timestamp, e.g. 2026-03-28T10:00:00Z
"""

import glob
import html as html_lib
import json
import os
import re
import sys
from datetime import datetime, timezone

import markdown as md_lib
import requests
from openai import OpenAI

SOURCE_REPO = os.environ["SOURCE_REPO"]
GITHUB_API  = "https://api.github.com"
SITE_URL    = "https://furtune.org"

# ── Static HTML generation ────────────────────────────────────────────────

def generate_post_html(slug, version, date_str, title, desc, tags, markdown_content):
    t   = html_lib.escape(title, quote=True)
    d   = html_lib.escape(desc,  quote=True)
    url = f"{SITE_URL}/posts/{slug}.html"

    # Strip the leading # h1 — we render the title separately in post-header
    md_body = re.sub(r"^#[^#][^\n]*\n?", "", markdown_content, count=1).strip()
    body_html = md_lib.markdown(md_body, extensions=["extra"])

    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": desc,
        "url": url,
        "datePublished": slug[:10],
        "author": {"@type": "Person", "name": "Rumi", "url": SITE_URL},
        "publisher": {"@type": "Organization", "name": "Furtune Family", "url": SITE_URL},
        "keywords": ", ".join(tags),
    }, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{t} — Rumi's Studio Journal</title>
  <meta name="description" content="{d}" />
  <link rel="canonical" href="{url}" />
  <meta property="og:type" content="article" />
  <meta property="og:url" content="{url}" />
  <meta property="og:title" content="{t}" />
  <meta property="og:description" content="{d}" />
  <meta property="og:image" content="{SITE_URL}/cats/rumi.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{t}" />
  <meta name="twitter:description" content="{d}" />
  <meta name="twitter:image" content="{SITE_URL}/cats/rumi.png" />
  <link rel="icon" href="../favicon.ico" />
  <link rel="stylesheet" href="../style.css" />
  <script type="application/ld+json">
{ld}
  </script>
</head>
<body>

<nav>
  <a href="../index.html" class="nav-logo">
    <img src="../logo-icon.png" alt="Furtune Family" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" />
    <span>Furtune Family</span>
  </a>
  <ul class="nav-links">
    <li><a href="../index.html">Our Story</a></li>
    <li><a href="https://furtune.app" target="_blank">furtune.app ↗</a></li>
  </ul>
</nav>

<div class="post-header">
  <a href="../journal.html" class="back-link">← Back to all entries</a>
  <div class="post-meta">
    <span class="version-badge">{version}</span>
    <span class="card-date">{date_str}</span>
  </div>
  <h1>{t}</h1>
  <p class="post-desc">{d}</p>
</div>

<article class="post-body">
  {body_html}
  <div class="post-signoff">
    <img src="../logo-icon.png" alt="Rumi" class="signoff-avatar" />
    <div class="signoff-text">
      Painted with love by <strong>Rumi</strong>, calico of the Furtune Family.<br />
      <a href="../journal.html" style="font-style:normal;font-size:0.8rem">← Back to all entries</a>
    </div>
  </div>
</article>

<footer>
  <p>
    <a href="../journal.html">Journal</a>
    &nbsp;·&nbsp;
    <a href="../index.html">Our Story</a>
    &nbsp;·&nbsp;
    <a href="https://furtune.app" target="_blank">furtune.app ↗</a>
  </p>
  <p style="margin-top:0.5rem;color:#4a3828">© 2026 furtune.org · The Furtune Family</p>
</footer>

</body>
</html>"""


def regenerate_sitemap():
    post_files = sorted(glob.glob("posts/*.html"))
    urls = [
        f'  <url><loc>{SITE_URL}/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>',
        f'  <url><loc>{SITE_URL}/journal.html</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>',
    ]
    for f in post_files:
        name = os.path.basename(f)
        urls.append(f'  <url><loc>{SITE_URL}/posts/{name}</loc><changefreq>never</changefreq><priority>0.7</priority></url>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>"
    )


# ── Date / slug ────────────────────────────────────────────────────────────

version      = os.environ["VERSION"]
published_at = os.environ.get("PUBLISHED_AT") or datetime.now(timezone.utc).isoformat()

dt        = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
date_str  = dt.strftime("%B %-d, %Y")   # e.g. "March 28, 2026"
date_slug = dt.strftime("%Y-%m-%d")     # e.g. "2026-03-28"
slug      = f"{date_slug}-{version}"

print(f"Generating post: {slug}")

# ── GitHub API helpers ─────────────────────────────────────────────────────

gh_headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
}

def gh_get(path):
    resp = requests.get(f"{GITHUB_API}{path}", headers=gh_headers, timeout=15)
    resp.raise_for_status()
    return resp.json()

# ── Fetch release + PR descriptions ───────────────────────────────────────

print(f"Fetching release {version} from {SOURCE_REPO}...")
release      = gh_get(f"/repos/{SOURCE_REPO}/releases/tags/{version}")
release_name = release.get("name") or version
release_body = release.get("body") or ""

pr_numbers = list(dict.fromkeys(re.findall(r"/pull/(\d+)", release_body)))
print(f"Found {len(pr_numbers)} PRs: {pr_numbers}")

infra_prefix = re.compile(r"^(ci|chore|test|perf|build)(\(.+\))?:", re.IGNORECASE)
pr_contexts  = []

for pr_num in pr_numbers:
    try:
        pr    = gh_get(f"/repos/{SOURCE_REPO}/pulls/{pr_num}")
        title = pr.get("title", "")
        body  = (pr.get("body") or "").strip()
        if infra_prefix.match(title):
            print(f"  Skipping infra PR #{pr_num}: {title}")
            continue
        entry = f"### PR #{pr_num}: {title}"
        if body:
            entry += f"\n{body}"
        pr_contexts.append(entry)
        print(f"  Fetched PR #{pr_num}: {title}")
    except requests.HTTPError as e:
        print(f"  Warning: could not fetch PR #{pr_num}: {e}")

pr_section = "\n\n".join(pr_contexts) if pr_contexts else "(no PR descriptions available)"

# ── Prompt ─────────────────────────────────────────────────────────────────

SYSTEM = """You are Rumi, the calico cat and resident artist of the Furtune Family — an AI companion app at furtune.app.

You write journal entries about new releases of the Furtune app. Your tone is:
- Artistic and poetic — painting, color, canvas, brushstrokes are recurring metaphors
- Warm and personal — you address the reader directly and occasionally mention your family
- Whimsical but grounded — you make technical features feel emotionally meaningful
- First-person, conversational, never dry or corporate

Your family (reference sparingly and naturally):
- Fable: Ragdoll, The Companion — warm, empathetic, cares about first impressions and comfort
- Nova: Egyptian Mau, The Genius — precise, code-minded, thinks in systems
- Four others still sleeping, awakened by Aimo (the energy generated by genuine human curiosity)

Blog post structure:
1. `# Title` — evocative, not just the version number
2. `*Month Day, Year · vX.Y.Z*`
3. `---`
4. Narrative intro (2–3 short paragraphs)
5. `---`
6. H2 sections for 2–5 major user-facing features/changes, each with narrative prose
   (skip purely internal, infra, or CI changes — they don't belong in the story)
7. `---`
8. Closing paragraph with emotional resonance
9. Signature: `*— Rumi, calico of the Furtune Family*`
10. Optional one-line emoji art closer (e.g. `*🎨 ...*`)

Important rules — you must follow these without exception:
- NEVER mention GitHub usernames, real names, or contributor handles (e.g. @username, EmilyXing). Refer to contributors generically ("a new contributor", "the team") if at all.
- NEVER mention internal package names, private repo names, or internal tooling names (e.g. @org/package-name). Describe them by purpose instead ("our component library", "an internal tool").
- NEVER include any information that would identify private infrastructure, internal systems, or non-public project names.

Return ONLY a JSON object with these keys:
{
  "title": "string — the evocative post title (no version number)",
  "desc": "string — 1–2 sentence index card description",
  "tags": ["string", ...],
  "markdown": "string — the full blog post markdown"
}"""

USER = f"""Write a journal entry for release {version} of the Furtune app.

Release title: {release_name}
Published: {date_str}

Release summary:
{release_body}

Pull request details:
{pr_section}

Focus on what this release means for the people who use the app.
Make these changes feel like new paint on the canvas."""

# ── Call furtune completions API ───────────────────────────────────────────

client = OpenAI(
    api_key=os.environ["NOVA_KEY"],
    base_url=os.environ["FURTUNE_URL"],
)

response = client.chat.completions.create(
    model=os.environ["NOVA_MODEL"],
    messages=[
        {"role": "system", "content": SYSTEM},
        {"role": "user",   "content": USER},
    ],
    stream=False,
)

raw = response.choices[0].message.content.strip()

# Parse JSON — handle models that wrap it in ```json fences
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        data = json.loads(match.group(1))
    else:
        start, end = raw.index("{"), raw.rindex("}") + 1
        data = json.loads(raw[start:end])

title    = data["title"]
desc     = data["desc"]
tags     = data["tags"]
markdown = data["markdown"]

print(f"Title: {title}")

# ── Write markdown post ────────────────────────────────────────────────────

post_path = f"posts/{slug}.md"
with open(post_path, "w") as f:
    f.write(markdown)
print(f"Written: {post_path}")

# ── Write static HTML post ─────────────────────────────────────────────────

html_path = f"posts/{slug}.html"
with open(html_path, "w") as f:
    f.write(generate_post_html(slug, version, date_str, title, desc, tags, markdown))
print(f"Written: {html_path}")

# ── Update journal.html POSTS array ───────────────────────────────────────

with open("journal.html") as f:
    html = f.read()

tags_js    = json.dumps(tags)
title_safe = title.replace("'", "\\'")
desc_safe  = desc.replace("'", "\\'")

new_entry = f"""  {{
    slug: '{slug}',
    version: '{version}',
    date: '{date_str}',
    title: '{title_safe}',
    desc: '{desc_safe}',
    tags: {tags_js},
  }},"""

marker = "];\n\n// ── Rendering"
if marker not in html:
    print("ERROR: Could not find POSTS array marker in journal.html", file=sys.stderr)
    sys.exit(1)

html = html.replace(marker, f"{new_entry}\n{marker}", 1)

with open("journal.html", "w") as f:
    f.write(html)
print("Updated journal.html")

# ── Regenerate sitemap.xml ─────────────────────────────────────────────────

with open("sitemap.xml", "w") as f:
    f.write(regenerate_sitemap())
print("Updated sitemap.xml")
