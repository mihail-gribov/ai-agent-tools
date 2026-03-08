"""Convert Markdown to Asana-compatible HTML (rich text).

Asana supports a limited subset of HTML in html_notes / html_text fields:
  <body>, <h1>, <h2>, <strong>, <em>, <u>, <s>, <code>,
  <ol>, <ul>, <li>, <a href>, <blockquote>, <pre>, <hr/>

All output must be wrapped in <body> tags and be valid XML.
"""

import re
from xml.sax.saxutils import escape


def md_to_html(text: str) -> str:
    """Convert markdown text to Asana-compatible HTML wrapped in <body>."""
    if not text or not text.strip():
        return "<body></body>"

    lines = text.split("\n")
    blocks: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(escape(lines[i]))
                i += 1
            if i < len(lines):
                i += 1  # skip closing ```
            blocks.append(f"<pre>{'&#10;'.join(code_lines)}</pre>")
            continue

        # Blank line — skip
        if not line.strip():
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
            blocks.append("<hr/>")
            i += 1
            continue

        # Header (h1 or h2 only — Asana limit)
        m = re.match(r"^(#{1,2})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            blocks.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Deeper headers (###+ ) — render as bold text
        m = re.match(r"^#{3,}\s+(.+)$", line)
        if m:
            blocks.append(f"<strong>{_inline(m.group(1))}</strong>")
            i += 1
            continue

        # Blockquote
        if line.lstrip().startswith("> ") or line.strip() == ">":
            quote_lines: list[str] = []
            while i < len(lines):
                s = lines[i]
                if s.lstrip().startswith("> "):
                    quote_lines.append(s.lstrip()[2:])
                elif s.strip() == ">":
                    quote_lines.append("")
                else:
                    break
                i += 1
            blocks.append(f"<blockquote>{_inline(' '.join(quote_lines))}</blockquote>")
            continue

        # Unordered list
        if re.match(r"^\s*[-*+]\s", line):
            items: list[str] = []
            while i < len(lines) and re.match(r"^\s*[-*+]\s", lines[i]):
                item_text = re.sub(r"^\s*[-*+]\s+", "", lines[i])
                # Strip checkbox markers
                item_text = re.sub(r"^\[[ x]\]\s*", "", item_text)
                items.append(f"<li>{_inline(item_text)}</li>")
                i += 1
            blocks.append(f"<ul>{''.join(items)}</ul>")
            continue

        # Ordered list
        if re.match(r"^\s*\d+[.)]\s", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s", lines[i]):
                item_text = re.sub(r"^\s*\d+[.)]\s+", "", lines[i])
                items.append(f"<li>{_inline(item_text)}</li>")
                i += 1
            blocks.append(f"<ol>{''.join(items)}</ol>")
            continue

        # Regular paragraph — collect consecutive non-block lines
        para_lines: list[str] = []
        while i < len(lines) and lines[i].strip() and not _is_block_start(lines[i]):
            para_lines.append(lines[i])
            i += 1
        blocks.append(_inline("\n".join(para_lines)))

    return f"<body>{''.join(blocks)}</body>"


def _is_block_start(line: str) -> bool:
    """Check if a line starts a new block-level element."""
    s = line.strip()
    if not s:
        return True
    return bool(
        s.startswith("```")
        or s.startswith("#")
        or s.startswith("> ")
        or s == ">"
        or re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", s)
        or re.match(r"^\s*[-*+]\s", line)
        or re.match(r"^\s*\d+[.)]\s", line)
    )


def _inline(text: str) -> str:
    """Convert inline markdown to HTML, handling code spans specially."""
    # Process code spans first — no formatting inside them
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(_format_text(text[last : m.start()]))
        parts.append(f"<code>{escape(m.group(1))}</code>")
        last = m.end()
    parts.append(_format_text(text[last:]))
    return "".join(parts)


def _format_text(text: str) -> str:
    """Apply inline formatting: bold, italic, strikethrough, links."""
    if not text:
        return ""
    # Escape HTML entities
    text = escape(text)
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # Italic: *text* or _text_ (but not mid-word underscores)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", text)
    # Strikethrough: ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    # Links: [text](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text
