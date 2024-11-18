from plaitime.parser import parse
import pytest


@pytest.mark.parametrize(
    "input, expected",
    [
        ("Hello *world*!", "Hello <em>world</em>!"),
        ("*All italic*", "<em>All italic</em>"),
        ("No italics here", "No italics here"),
        ("*First* and *second* italic", "<em>First</em> and <em>second</em> italic"),
        (
            "Text with *multiple* words in *italic* style",
            "Text with <em>multiple</em> words in <em>italic</em> style",
        ),
        # Edge cases
        ("Unclosed asterisk*", "Unclosed asterisk"),
        ("**", ""),  # Double asterisk
        ("", ""),  # Empty string
        ("*Unclosed asterisk", "<em>Unclosed asterisk</em>"),
        # ("* foo*", "<em> foo</em>"),
        ("*foo bar baz", "<em>foo bar baz</em>"),
        ("*foo\nbar*", "<em>foo<br/>bar</em>"),
        (
            "A line*foo*\n\n*bar* Another line." "",
            "A line<em>foo</em><br/><br/><em>bar</em> Another line.",
        ),
    ],
)
def test_parse(input, expected):
    got = parse(input)
    assert got == expected
