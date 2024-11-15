from . import CHARACTERS_PER_TOKEN
from .data_models import Message
import ollama
from pydantic import BaseModel
import logging
from typing import TypeVar
import re

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def estimate_num_tokens(prompt: str, messages: list[Message]):
    # estimate number of token
    num_char = len(prompt)
    for m in messages:
        num_char += len(m.content)
    return num_char / CHARACTERS_PER_TOKEN


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
            if not re.match(r"^[\s\.]+$", s[index:]):
                break
            if index == 0:
                break
    return s[:index].rstrip()
