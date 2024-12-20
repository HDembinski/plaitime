def parse(text: str) -> str:
    """
    Convert text containing markdown-style italic markers (*) and newlines to HTML.

    Args:
        text (str): Input text

    Returns:
        str: HTML code
    """
    parts = text.split("*")

    result = []
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2 == 0:
            # Even indices are normal text
            result.append(part)
        else:
            # Odd indices are emphasized text
            result.append(f"<em>{part}</em>")

    return "".join(result).replace("\n", "<br/>").replace(r"'", r"\'")
