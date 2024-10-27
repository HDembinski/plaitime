from dataclasses import dataclass, field
from typing import List


@dataclass
class Character:
    name: str = "Assistant"
    prompt: str = ""
    model: str = "llama3.2"
    temperature: float = 0.7
    conversation: List[str] = field(default_factory=list)


@dataclass
class Config:
    current_character: str = "Assistant"
