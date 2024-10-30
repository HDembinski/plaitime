from pai import CHARACTERS_PER_TOKEN


def estimate_num_tokens(prompt, conversation):
    # estimate number of token
    num_char = len(prompt)
    for message in conversation:
        num_char += len(message["content"])
    return num_char / CHARACTERS_PER_TOKEN
