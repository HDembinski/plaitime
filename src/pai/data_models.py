from pydantic import BaseModel, PositiveFloat
from typing import Literal
import numpy as np


class Character(BaseModel):
    name: str = "Assistant"
    prompt: str = ""
    model: str = "llama3.2"
    temperature: PositiveFloat = 0.7
    save_conversation: bool = True


class Message(BaseModel):
    role: str
    content: str


# class Fact(BaseModel):
#     kind: Literal[
#         "character_trait", "relationship", "event", "backstory", "world_building"
#     ]
#     content: str
#     characters: set[str]  # Characters involved in this fact
#     timestamp: str = ""
#     embedding: np.ndarray | None = None


class Fact(BaseModel):
    content: str


class Memory(BaseModel):
    messages: list[Message] = []
    facts: list[Fact] = []


class Config(BaseModel):
    current_character: str = ""
