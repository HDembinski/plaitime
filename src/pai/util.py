from pai import CHARACTERS_PER_TOKEN
from pai.data_models import Message


def estimate_num_tokens(prompt: str, conversation: list[Message]):
    # estimate number of token
    num_char = len(prompt)
    for message in conversation:
        num_char += len(message.content)
    return num_char / CHARACTERS_PER_TOKEN
