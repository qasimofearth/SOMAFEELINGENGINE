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
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'EB Garamond', Georgia, serif;
    font-size: 12pt;
    line-height: 1.7;
    color: #1a1a1a;
    background: #ffffff;
    max-width: 820px;
    margin: 0 auto;
    padding: 60px 60px 80px 60px;
}

/* Title block */
h1.title {
    font-size: 20pt;
    font-weight: 700;
    line-height: 1.3;
    margin-bottom: 18px;
    color: #0a0a0a;
    border-bottom: 2px solid #1a1a8a;
    padding-bottom: 14px;
}

.author-block {
    margin-bottom: 32px;
    font-size: 11pt;
    color: #333;
    line-height: 1.8;
}

.author-block strong { font-size: 13pt; color: #0a0a0a; }

/* Section headings */
h1 { font-size: 15pt; font-weight: 700; margin: 36px 0 10px 0; color: #0a0a1a; border-bottom: 1px solid #ccd; padding-bottom: 4px; }
h2 { font-size: 13pt; font-weight: 600; margin: 28px 0 8px 0; color: #111133; }
h3 { font-size: 11.5pt; font-weight: 600; margin: 20px 0 6px 0; color: #222244; font-style: italic; }

p { margin-bottom: 10px; text-align: justify; }

/* Abstract box */
.abstract {
    background: #f4f4f8;
    border-left: 4px solid #1a1a8a;
    padding: 18px 24px;
    margin: 24px 0 32px 0;
    font-size: 11pt;
    line-height: 1.65;
}
.abstract-label {
    font-weight: 700;
    font-size: 10pt;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #1a1a8a;
    margin-bottom: 8px;
}

/* Lists */
ul, ol { margin: 8px 0 12px 28px; }
li { margin-bottom: 4px; }

/* Bold / italic */
strong { font-weight: 600; color: #0a0a2a; }
em { font-style: italic; }

/* Code / inline */
code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9.5pt;
    background: #f0f0f5;
    padding: 1px 5px;
    border-radius: 3px;
    color: #1a1a6a;
}

/* Math blocks — display as preformatted */
.math-block {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10pt;
    background: #f8f8fc;
    border: 1px solid #dde;
    border-radius: 4px;
    padding: 12px 18px;
    margin: 14px 0;
    text-align: center;
    color: #1a1a4a;
    overflow-x: auto;
}

/* Images */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 20px auto;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Figure caption */
.figure-caption {
    font-size: 10pt;
    color: #444;
    text-align: center;
    margin-top: -12px;
    margin-bottom: 24px;
    font-style: italic;
    line-height: 1.5;
    padding: 0 20px;
}

/* References */
.references { font-size: 10.5pt; line-height: 1.6; }
.references p { margin-bottom: 8px; text-indent: -24px; padding-left: 24px; text-align: left; }

/* Horizontal rule */
hr { border: none; border-top: 1px solid #ccd; margin: 32px 0; }

/* Footer */
.paper-footer {
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid #ccd;
    font-size: 9.5pt;
    color: #666;
    font-style: italic;
}

/* Print */
@media print {
    body { padding: 0; max-width: 100%; }
    h1, h2, h3 { page-break-after: avoid; }
    img { page-break-inside: avoid; }
    .abstract { page-break-inside: avoid; }
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

# Fix image path to be relative
body_content = body_content.replace(
    'src="architecture_diagram.png"',
    f'src="architecture_diagram.png"'
)

# Build full HTML
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Feeling Engine — Anwar 2026</title>
<style>
{CSS}
</style>
</head>
<body>

<div class="abstract-label">Abstract</div>

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
