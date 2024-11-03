import ollama
from PySide6 import QtCore
from pai import CONTEXT_MARGIN, CHARACTERS_PER_TOKEN
from pai.data_models import Fact, Character
from pai.message_widget import MessageWidget
import logging
import json

logger = logging.getLogger(__name__)


class Generator(QtCore.QThread):
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)
    updatedFacts = QtCore.Signal(object)

    def __init__(
        self,
        character: Character,
        widgets: list[MessageWidget],
        context_size: int,
        *,
        memory_model: str = "llama3.2",
    ):
        super().__init__()
        self.memory_model = memory_model
        self.character = character
        self.widgets = widgets
        self.context_size = context_size
        self.interrupt = False

    def run(self):
        system_prompt = self.character.prompt or "You are a helpful AI assistant."
        widgets = self.widgets

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        conversation_window = []
        num_token = len(system_prompt) / CHARACTERS_PER_TOKEN
        for w in reversed(widgets):
            num_token += len(w.content) / CHARACTERS_PER_TOKEN
            if num_token > self.context_size - CONTEXT_MARGIN:
                break
            conversation_window.append({"role": w.role, "content": w.content})
        conversation_window.append({"role": "system", "content": system_prompt})
        conversation_window.reverse()

        user = conversation_window[-1]
        user_input = user["content"]

        facts = widgets[-2].facts if len(widgets) >= 2 else []
        if facts:
            user["content"] = EXTENDED_PROMPT.format(
                message=user_input,
                fact_list="\n".join(f"* {x.content}" for x in self.facts),
            )
            logger.info(f"user message with added context\n{user['content']}")

        new_message = ""
        try:
            for response in ollama.chat(
                model=self.character.model,
                messages=conversation_window,
                stream=True,
                options={"temperature": self.character.temperature},
            ):
                if self.interrupt:
                    return
                chunk = response["message"]["content"]
                self.nextChunk.emit(chunk)
                new_message += chunk
        except Exception as e:
            error_message = f"""Error generating response: {str(e)}\n\n
Please make sure that the model '{self.character.model}' is available.
You can run 'ollama run {self.character.model}' in terminal to check."""
            self.error.emit(error_message)

        # facts = self.extract_facts(f"{user_input}\n\n{new_message}")
        self.updatedFacts.emit(facts)

    def extract_facts(self, excerpt: str) -> list[Fact]:
        prompt = EXTRACTION_PROMPT.format(excerpt)
        data = generate_list_response(self.memory_model, prompt)
        facts = self.facts + [
            Fact(content=x["content"], characters=x.get("characters", [])) for x in data
        ]

        s = "\n".join(f"{i+1}. {x.content}" for (i, x) in enumerate(facts))
        logger.info(f"Before removal of redundancies:\n{s}")

        enumerated_list = []
        for i, x in enumerate(facts):
            enumerated_list.append(f"{i+1}. {x.content}")
        prompt = DUPLICATION_PROMPT.format("\n".join(enumerated_list))
        indices = generate_list_response(self.memory_model, prompt, item_type=int)
        for i in indices:
            if i >= 1 and i <= len(facts):
                del facts[i - 1]

        s = "\n".join(f"{i+1}. {x.content}" for (i, x) in enumerate(facts))
        logger.info(f"After removal of redundancies:\n{s}")
        return facts


def generate_list_response(
    model: str, prompt: str, item_type: type | None = None
) -> list:
    for iter in range(5):
        response: str = ollama.generate(
            model=model, prompt=prompt, options={"temperature": 0.1}
        )["response"]
        logger.info(f"Raw response (iter={iter}):\n{response}")
        # clip comments before or after the json
        try:
            clipped = response[response.index("[") : response.rindex("]") + 1]
            list_of_data = json.loads(clipped)
            if item_type is None:
                return list_of_data
            return [item_type(x) for x in list_of_data]
        except Exception as e:
            logger.error("JSON parsing failed (iter={iter}):", e)
    return []


EXTENDED_PROMPT = """
# User message
{message}

# Context
{fact_list}
"""

EXTRACTION_PROMPT = """
You are a professional author.

Analyze the following story excerpt and extract facts from the story.

# Story excerpt

{0}

# Instructions

Think aloud about the excerpt, as you are trying to isolate facts which are established and are of long-term importance to continue the story. Ignore transient or fleeting information.

Focus on:
* Character descriptions
  - How old is the character?
  - How do they look like (any details about face or body)?
  - How are they dressed?
  - What is their occupation? Do they mention hobbies?
  - Do they behave in a typical way?
  - What did they reveal about their backstory?
* Relationships between characters
  - Are the characters friends or enemies, close or distant?
  - Are they flirting or in love? Is the love one-sided?
  - Do the characters know each other well or not?
* World-building details
  - Where and when does the story happen?
  - Descriptions of places
* Central events that will certainly shape the future of the story

When you are done analying, return the facts in JSON format. Example:

[
    {{
        "content": "content of the first fact",
        "characters" : ["list", "of", "involved", "characters"]
    }},
    {{
        "content": "content of the second fact",
        "characters" : ["another", "list", "of", "involved", "characters"]
    }}
]

If the fact is not related to any character specifically, leave the "characters" list empty.
"""

DUPLICATION_PROMPT = """
You are a professional author.

Try to find redundant information in the following list of story facts. Think aloud about the list and why certain items seem redundant.
Redundant items are describing the same thing in different words.

Once you are done analyzing, return the indices of the facts that can safely be removed, formatted as a JSON list.
If you don't find anything that is redundant, return an empty list. If you are not perfectly sure, it is better to NOT remove an item. In other words, only include indices in the list,
if you are very confident that they are redundant.

# Enumerated list of story facts

{0}
"""
