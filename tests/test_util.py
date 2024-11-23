from plaitime.util import remove_last_sentence
import pytest


@pytest.mark.parametrize(
    "input,expected",
    (
        ("", ""),
        ("  \n  \n  ", ""),
        ("\n", ""),
        ("\n\n\n", ""),
        ("Single line.", ""),
        ("First line. Second line.", "First line."),
        ("First line. Second line. Third line.", "First line. Second line."),
        ("First sentence. Second sentence...", "First sentence."),
        ("First line.\n\nSecond line.", "First line."),
        ("First line.\nSecond\tline.\nThird\tline.", "First line.\nSecond\tline."),
        ("First line! Second line!", "First line!"),
        ("First line? Second line?", "First line?"),
        ('First line. "Second line. Third line."', 'First line. "Second line."'),
        ('First line. "Second line."', "First line."),
        (
            'First line. "Second", he says, "line."',
            "First line.",
        ),
        (
            "First line. *Second line*.",
            "First line.",
        ),
        (
            "First line. *Second line. Third line.*",
            "First line. *Second line.*",
        ),
        (
            'First line. "*Second* line."',
            "First line.",
        ),
        (
            'First line. "*Second line.*"',
            "First line.",
        ),
        (
            'First line. "*Second line. Third line.*"',
            'First line. "*Second line.*"',
        ),
        (
            "First line. (Second line.)",
            "First line.",
        ),
        (
            "First line. (Second line. Third line.)",
            "First line. (Second line.)",
        ),
    ),
)
def test_basic_multiline_string(input, expected):
    assert remove_last_sentence(input) == expected
