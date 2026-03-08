"""Tests for markdown-to-Asana-HTML conversion."""

from asana_cli.rich_text import md_to_html


def test_empty_input():
    assert md_to_html("") == "<body></body>"
    assert md_to_html("   ") == "<body></body>"
    assert md_to_html(None) == "<body></body>"


def test_plain_text():
    assert md_to_html("Hello world") == "<body>Hello world</body>"


def test_html_entities_escaped():
    assert md_to_html("a < b & c > d") == "<body>a &lt; b &amp; c &gt; d</body>"


def test_h1():
    assert md_to_html("# Title") == "<body><h1>Title</h1></body>"


def test_h2():
    assert md_to_html("## Section") == "<body><h2>Section</h2></body>"


def test_h3_rendered_as_bold():
    assert md_to_html("### Subsection") == "<body><strong>Subsection</strong></body>"


def test_bold():
    assert md_to_html("**bold**") == "<body><strong>bold</strong></body>"


def test_italic():
    assert md_to_html("*italic*") == "<body><em>italic</em></body>"


def test_strikethrough():
    assert md_to_html("~~removed~~") == "<body><s>removed</s></body>"


def test_inline_code():
    assert md_to_html("`code`") == "<body><code>code</code></body>"


def test_inline_code_no_formatting_inside():
    result = md_to_html("`**not bold**`")
    assert "<strong>" not in result
    assert "<code>**not bold**</code>" in result


def test_link():
    result = md_to_html("[click](https://example.com)")
    assert result == '<body><a href="https://example.com">click</a></body>'


def test_unordered_list():
    text = "- one\n- two\n- three"
    result = md_to_html(text)
    assert result == "<body><ul><li>one</li><li>two</li><li>three</li></ul></body>"


def test_unordered_list_asterisk():
    text = "* one\n* two"
    result = md_to_html(text)
    assert result == "<body><ul><li>one</li><li>two</li></ul></body>"


def test_ordered_list():
    text = "1. first\n2. second"
    result = md_to_html(text)
    assert result == "<body><ol><li>first</li><li>second</li></ol></body>"


def test_checkbox_stripped():
    text = "- [ ] todo\n- [x] done"
    result = md_to_html(text)
    assert result == "<body><ul><li>todo</li><li>done</li></ul></body>"


def test_code_block():
    text = "```\nfoo\nbar\n```"
    result = md_to_html(text)
    assert result == "<body><pre>foo&#10;bar</pre></body>"


def test_code_block_with_language():
    text = "```python\nprint('hi')\n```"
    result = md_to_html(text)
    assert "<pre>" in result
    assert "print(&#39;hi&#39;)" in result or "print('hi')" in result


def test_blockquote():
    text = "> This is a quote"
    result = md_to_html(text)
    assert result == "<body><blockquote>This is a quote</blockquote></body>"


def test_horizontal_rule():
    assert "<hr/>" in md_to_html("---")
    assert "<hr/>" in md_to_html("***")
    assert "<hr/>" in md_to_html("___")


def test_mixed_content():
    text = """## Agreed solution

Clear description here.

### Key decisions
- decision one
- decision two

### How to verify
1. step one
2. step two"""
    result = md_to_html(text)
    assert "<h2>Agreed solution</h2>" in result
    assert "<strong>Key decisions</strong>" in result
    assert "<ul>" in result
    assert "<li>decision one</li>" in result
    assert "<ol>" in result
    assert "<li>step one</li>" in result


def test_paragraph_separation():
    text = "First paragraph.\n\nSecond paragraph."
    result = md_to_html(text)
    assert "First paragraph." in result
    assert "Second paragraph." in result


def test_body_wrapper():
    result = md_to_html("test")
    assert result.startswith("<body>")
    assert result.endswith("</body>")


def test_bold_inside_list():
    text = "- **important** item"
    result = md_to_html(text)
    assert "<li><strong>important</strong> item</li>" in result
