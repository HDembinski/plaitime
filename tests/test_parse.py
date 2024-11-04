from plaitime.parser import parse
import pytest


@pytest.mark.parametrize(
    "input, expected",
    [
        ("Hello *world*!", "Hello <i>world</i>!"),
        ("*All italic*", "<i>All italic</i>"),
        ("No italics here", "No italics here"),
        ("*First* and *second* italic", "<i>First</i> and <i>second</i> italic"),
        (
            "Text with *multiple* words in *italic* style",
            "Text with <i>multiple</i> words in <i>italic</i> style",
        ),
        # Edge cases
        ("Unclosed asterisk*", "Unclosed asterisk"),
        ("**", ""),  # Double asterisk
        ("", ""),  # Empty string
        ("*Unclosed asterisk", "<i>Unclosed asterisk</i>"),
    ],
)
def test_parse(input, expected):
    got = parse(input)
    assert got == expected
