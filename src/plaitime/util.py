from . import CHARACTERS_PER_TOKEN, SESSION_DIRECTORY
from .data_models import Message
import ollama
from pydantic import BaseModel
import logging
from typing import TypeVar
import re

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def get_session_names():
    names = []
    for fname in SESSION_DIRECTORY.glob("*.json"):
        names.append(fname.stem)
    return names


def estimate_num_tokens(messages: list[Message], *args: str) -> int:
    # estimate number of token
    num_char = 0
    for arg in args:
        num_char += len(arg)
    for m in messages:
        num_char += len(m.content)
    return int(num_char / CHARACTERS_PER_TOKEN)


def generate_json_response(
    model: str, prompt: str, data_model: T, *, trials: int = 5
) -> T | None:
    for trial in range(trials):
        response: str = ollama.generate(
            model=model, prompt=prompt, options={"temperature": 0.1}
        )["response"]
        logger.info(f"Raw response (trial={trial}):\n{response}")
        # clip comments before or after the json
        try:
            clipped = response[response.index("{") : response.rindex("}") + 1]
            return data_model.model_validate(clipped)
        except Exception as e:
            logger.error("JSON parsing failed (trial={trial}):", e)
    return None


def remove_last_sentence(s: str) -> str:
    index = len(s)
    trailing = ""
    if index > 0:
        for _ in range(10):
            index = (
                max(
                    s.rfind(".", 0, index - 1),
                    s.rfind("!", 0, index - 1),
                    s.rfind("?", 0, index - 1),
                )
                + 1
            )
            if not re.match(r"^[\s\"\*'\.\(\)]+$", s[index:]):
                break
            if index == 0:
                break
        removed = s[index:]
        trail = []
        for c in r"'\"*":
            if removed.count(c) % 2 == 1:
                trail.append((removed.index(c), c))
        trailing = "".join(x[1] for x in sorted(trail))
        if ")" in removed and "(" not in removed:
            trailing += ")"
    return s[:index].rstrip() + trailing


def shorten_string(s: str, maxlen: int = 1000):
    if len(s) > maxlen:
        return f"{s[:497]} [...] {s[504:]}"
    return s
