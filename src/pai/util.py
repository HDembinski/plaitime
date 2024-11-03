from pai import CHARACTERS_PER_TOKEN
from pai.data_models import Message


def estimate_num_tokens(prompt: str, messages: list[Message]):
    # estimate number of token
    num_char = len(prompt)
    for m in messages:
        num_char += len(m.content)
    return num_char / CHARACTERS_PER_TOKEN
