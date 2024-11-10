from plaitime.util import remove_last_sentence


def test_basic_multiline_string():
    input_str = "First line. Second line. Third line."
    expected = "First line. Second line."
    assert remove_last_sentence(input_str) == expected


def test_empty_string():
    assert remove_last_sentence("") == ""


def test_all_whitespace():
    input_str = "  \n  \n  "
    expected = ""
    assert remove_last_sentence(input_str) == expected


def test_single_newline():
    assert remove_last_sentence("\n") == ""


def test_multiple_newlines_only():
    assert remove_last_sentence("\n\n\n") == ""


def test_single_line():
    assert remove_last_sentence("Single line.") == ""


def test_single_line_no_period():
    assert remove_last_sentence("Single line") == ""


def test_sentence_ends_in_dots():
    input_str = "First sentence. Second sentence..."
    expected = "First sentence."
    assert remove_last_sentence(input_str) == expected


def test_only_whitespace_last_line():
    input_str = "First line.\nSecond line.\n    \t    "
    expected = "First line."
    assert remove_last_sentence(input_str) == expected


def test_whitespace_between_lines():
    input_str = "First line.\n  \n  \nLast line.\n  \n"
    expected = "First line."
    assert remove_last_sentence(input_str) == expected


# Edge cases
def test_string_with_tabs():
    input_str = "First line.\nSecond\tline.\nThird\tline."
    expected = "First line.\nSecond\tline."
    assert remove_last_sentence(input_str) == expected
