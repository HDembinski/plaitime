from pydantic import BaseModel, PositiveFloat


class Character(BaseModel):
    name: str = "Assistant"
    prompt: str = ""
    model: str = "llama3.2"
    temperature: PositiveFloat = 0.7
    save_conversation: bool = True


class Message(BaseModel):
    role: str
    content: str


class Memory(BaseModel):
    messages: list[Message] = []


class Config(BaseModel):
    current_character: str = ""
