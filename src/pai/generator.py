import ollama
from PySide6 import QtCore
from pai import CONTEXT_MARGIN, CHARACTERS_PER_TOKEN
from pai.data_models import Fact, Character
from pai.message_widget import MessageWidget
import logging
import re

logger = logging.getLogger(__name__)


class Generator(QtCore.QThread):
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)
    updatedFacts = QtCore.Signal(object)

    def __init__(
        self,
        character: Character,
        messages: list[MessageWidget],
        facts: list[Fact],
        context_size: int,
        *,
        memory_model: str = "llama3.2",
    ):
        super().__init__()
        self.memory_model = memory_model
        self.character = character
        self.messages = messages
        self.facts = facts
        self.context_size = context_size
        self.interrupt = False

    def run(self):
        system_prompt = self.character.prompt or "You are a helpful AI assistant."
        messages = self.messages

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        conversation_window = []
        num_token = len(system_prompt) / CHARACTERS_PER_TOKEN
        i = len(messages) - 1
        while num_token < self.context_size - CONTEXT_MARGIN and i >= 0:
            message = messages[i]
            conversation_window.append(message.dict())
            i -= 1
            num_token += len(message.content) / CHARACTERS_PER_TOKEN
        conversation_window.reverse()

        user = conversation_window[-1]
        user_input = user["content"]
        if self.facts:
            user["content"] = EXTENDED_PROMPT.format(
                message=user_input,
                fact_list="\n".join(f"* {x.content}" for x in self.facts),
            )

        logger.info(user["content"])

        new_message = ""
        try:
            for response in ollama.chat(
                model=self.character.model,
                messages=[{"role": "system", "content": system_prompt}]
                + conversation_window,
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

        conversation_window.append({"role": "assistant", "content": new_message})

        # restore original user message for fact extraction
        user["content"] = user_input

        facts = self.extract_new_facts(conversation_window)
        if facts:
            self.updatedFacts.emit(facts)

    def extract_new_facts(
        self, conversation_window: list[dict[str, str]]
    ) -> list[Fact]:
        excerpt = "\n\n".join(m["content"] for m in conversation_window[-10:])

        known_facts = ""
        if self.facts:
            fact_list = "\n".join(f"* {x.content}" for x in self.facts)
            known_facts = KNOWN_FACTS_PROMPT.format(fact_list=fact_list)
        prompt = EXTRACTION_PROMPT.format(known_facts=known_facts, excerpt=excerpt)
        logger.info(prompt)

        response = ollama.generate(
            model=self.memory_model,
            prompt=prompt,
        )["response"]
        logger.info(f"Story facts:\n{response}")

        matches = re.findall(r"^ *\* *(.+)$", response, re.MULTILINE)
        logger.info("Parsed story facts:\n" + "\n".join(matches))

        return [Fact(content=x) for x in matches]


EXTENDED_PROMPT = """
# User message        
{message}

# Context
{fact_list}
"""

EXTRACTION_PROMPT = """
Analyze the following excerpt and extract facts.

Focus on:
* Character traits and descriptions
* Relationships between characters
* Important events or actions
* Character backstory elements
* World-building details

Facts must be explicitly established by the excerpt. Only focus on facts with a long-term relevance to the story.

# Response formatting

Return a list of facts in Markdown notation and nothing else. Use one line per story fact. Example:
* It is Sunday evening.
* Alice and Bob had a long discussion about marshmellows.
{known_facts}
# Story excerpt

{excerpt}
"""

KNOWN_FACTS_PROMPT = """
# Known facts

Here is a list of previously extracted facts. Update this list with new information you extract from the excerpt. Include all items from this list that are not updated in your response.

{fact_list}
"""
