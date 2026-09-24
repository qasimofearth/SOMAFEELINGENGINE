"""
Build a styled HTML version of the Feeling Engine paper, then convert to PDF
using pandoc's HTML pipeline.
"""
import subprocess
import os

here = os.path.dirname(os.path.abspath(__file__))
md_path = os.path.join(here, "FEELING_ENGINE_PAPER.md")
html_path = os.path.join(here, "FEELING_ENGINE_PAPER.html")

CSS = """
@import url('https://cdn.jsdelivr.net/gh/aaaakshat/cm-web-fonts@latest/font/Serif/cmun-serif.css');
@import url('https://cdn.jsdelivr.net/gh/aaaakshat/cm-web-fonts@latest/font/Typewriter/cmun-typewriter.css');

:root { color-scheme: light; --ink: #111; --muted: #555; --rule: #111; --link: #1f3a7a; }

* { box-sizing: border-box; }

body {
    font-family: 'Computer Modern Serif', 'Latin Modern Roman', 'CMU Serif', Georgia, serif;
    font-size: 17px;
    line-height: 1.5;
    color: var(--ink);
    background: #fff;
    max-width: 720px;
    margin: 0 auto;
    padding: 64px 24px 80px;
    hyphens: auto;
    -webkit-hyphens: auto;
    text-rendering: optimizeLegibility;
}

a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Title block ── */
.titleblock { text-align: center; margin-bottom: 2.2em; }
.titleblock h1 {
    font-size: 1.72em; font-weight: bold; line-height: 1.25;
    margin: 0 0 0.9em; border: none; padding: 0; hyphens: none;
}
.titleblock p { margin: 0.15em 0; text-indent: 0 !important; text-align: center; }
.author { font-size: 1.15em; }
.affil { font-style: italic; }
.date { color: var(--muted); font-size: 0.92em; }

/* ── Abstract ── */
.abstract { margin: 0 auto 2.4em; max-width: 88%; font-size: 0.92em; }
.abstract p { text-indent: 1.5em; }
.abstract p:first-child { text-align: center; text-indent: 0; margin-bottom: 0.5em; }
.abstract-title { font-weight: bold; font-size: 1.02em; }
.abstract p:first-child + p { text-indent: 0; }
.abstract p:last-child { text-indent: 0; margin-top: 0.8em; }

/* ── Headings (LaTeX article) ── */
h1, h2, h3, h4 { font-weight: bold; line-height: 1.3; hyphens: none; page-break-after: avoid; }
h2 { font-size: 1.3em; margin: 2em 0 0.7em; }
h3 { font-size: 1.1em; margin: 1.6em 0 0.5em; }
h4 { font-size: 1em; margin: 1.3em 0 0.4em; }

/* ── Body text: justified, indented paragraphs, no gaps ── */
p { margin: 0; text-align: justify; }
p + p { text-indent: 1.5em; }
ul, ol { margin: 0.6em 0 0.8em; padding-left: 1.8em; }
li { margin-bottom: 0.25em; text-align: justify; }
li p + p { text-indent: 0; }
ul + p, ol + p, .table-wrap + p, figure + p, blockquote + p, mjx-container + p { text-indent: 0; }

blockquote { margin: 1em 2em; font-size: 0.95em; }
blockquote p { text-indent: 0 !important; }

strong { font-weight: bold; }
code {
    font-family: 'Computer Modern Typewriter', 'Courier New', monospace;
    font-size: 0.95em;
}

hr { display: none; }

/* ── Math ── */
mjx-container[display="true"] { margin: 0.9em 0 !important; overflow-x: auto; overflow-y: hidden; max-width: 100%; }
mjx-container { max-width: 100%; }
body { overflow-wrap: break-word; }
html { overflow-x: hidden; }

/* ── Tables: booktabs style, numbered captions above ── */
body { counter-reset: table; }
.table-wrap { overflow-x: auto; margin: 1.4em 0; }
table { border-collapse: collapse; width: 100%; font-size: 0.8em; line-height: 1.35; counter-increment: table; }
caption {
    caption-side: top; text-align: left; font-size: 1.12em;
    margin-bottom: 0.6em; line-height: 1.4;
}
caption::before { content: "Table " counter(table) ". "; font-weight: bold; }
thead tr { border-top: 1.5px solid var(--rule); border-bottom: 0.8px solid var(--rule); }
tbody tr:last-child { border-bottom: 1.5px solid var(--rule); }
th { font-weight: bold; text-align: left; padding: 0.45em 0.6em; vertical-align: bottom; }
td { padding: 0.32em 0.6em; vertical-align: top; text-align: left; }
th:first-child, td:first-child { padding-left: 0; }
th:last-child, td:last-child { padding-right: 0; }

/* ── Figures ── */
figure { margin: 1.6em 0 0.4em; }
figure img, img { display: block; max-width: 100%; height: auto; margin: 0 auto; }
.fig-caption { font-size: 0.88em; text-align: justify; text-indent: 0 !important; margin: 0 0 1.6em; }
.fig-caption .lbl { font-weight: bold; }

/* ── References ── */
.references { font-size: 0.88em; }
.references p { text-indent: -1.8em !important; padding-left: 1.8em; margin-bottom: 0.45em; text-align: left; }

/* ── Footer ── */
.paper-footer {
    margin-top: 3em; padding-top: 0.8em; border-top: 0.6px solid #999;
    font-size: 0.8em; color: var(--muted); text-align: center;
}

@media (max-width: 600px) {
    body { font-size: 16px; padding: 32px 16px 56px; }
    .abstract { max-width: 100%; }
    blockquote { margin: 1em 1em; }
    p { text-align: left; }
}

@page { size: letter; margin: 1in; }
@media print {
    body { max-width: none; padding: 0; font-size: 11pt; }
    a { color: inherit; }
    figure, .table-wrap, .fig-caption { page-break-inside: avoid; }
    figure { page-break-after: avoid; }
    h2, h3, h4 { page-break-after: avoid; }
}
"""

# Read markdown
with open(md_path, "r") as f:
    md = f.read()

# Build HTML via pandoc
result = subprocess.run(
    [
        "pandoc",
        "-f", "markdown+tex_math_dollars",
        "-t", "html5",
        "--mathjax",
        "--standalone",
        f"--css=data:text/css,",
        "-",
    ],
    input=md.encode(),
    capture_output=True,
)

pandoc_html = result.stdout.decode()

# Extract just the body content
import re
body_match = re.search(r"<body[^>]*>(.*?)</body>", pandoc_html, re.DOTALL)
body_content = body_match.group(1) if body_match else pandoc_html

# Academic post-processing:
#  - figures: drop pandoc's alt-text figcaption; the bold "Figure N." paragraph
#    that follows each image in the markdown becomes the caption
#  - tables: unwrap <p> in captions (numbered by CSS counter), wrap for mobile scroll
body_content = re.sub(r"<figcaption[^>]*>.*?</figcaption>", "", body_content, flags=re.DOTALL)
body_content = re.sub(
    r"<p><strong>(Figure \d+\.)\s*(.*?)</strong>",
    lambda m: f'<p class="fig-caption"><span class="lbl">{m.group(1)}</span> '
              + (f'<em>{m.group(2)}</em>' if m.group(2).strip() else ''),
    body_content, flags=re.DOTALL,
)
body_content = re.sub(r"<caption>\s*<p>(.*?)</p>\s*</caption>", r"<caption>\1</caption>",
                      body_content, flags=re.DOTALL)
body_content = body_content.replace("<table", '<div class="table-wrap"><table').replace("</table>", "</table></div>")

# Build full HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Can AI Feel? The Feeling Engine — Anwar 2026</title>
<meta name="description" content="Can an AI feel? A continuously running affective substrate — brain, body, memory, and a ~14,000-word valence architecture — for a language model.">
<script>
window.MathJax = {{ chtml: {{ scale: 0.95 }} }};
</script>
<script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
<style>
{CSS}
</style>
</head>
<body>

{body_content}

<div class="paper-footer">
The Feeling Engine source: github.com/qasimofearth/SOMAFEELINGENGINE &nbsp;·&nbsp;
Live deployment: somafeelingengine.up.railway.app &nbsp;·&nbsp;
© 2026 Qasim Muhammad Anwar / The Source Library
</div>

</body>
</html>"""

with open(html_path, "w") as f:
    f.write(html)

print(f"HTML built: {html_path}")
print("Open in browser and File → Print → Save as PDF")
