from dataclasses import dataclass, field
from typing import List


@dataclass
class Character:
    name: str = "Assistant"
    prompt: str = "You are a helpful AI assistant."
    model: str = "llama3.2"
    temperature: float = 0.7
    conversation: List[str] = field(default_factory=list)
    append_global_prompt: bool = True


@dataclass
class Config:
    current_character: str = "Assistant"
    general_prompt: str = (
        "Use Markdown in your responses. When you describe actions, "
        "use the third-person for yourself and asterisks as markup. "
        "Example: *smiles and winks at you* Hi, I am your chat partner!",
    )
