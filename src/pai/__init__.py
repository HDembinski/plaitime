from pathlib import Path

BASE_DIRECTORY = Path.home() / ".pai"
BASE_DIRECTORY.mkdir(exist_ok=True)

CONFIG_FILE_NAME = BASE_DIRECTORY / "pai.cfg"
CHARACTER_DIRECTORY = BASE_DIRECTORY / "characters"
CHARACTER_DIRECTORY.mkdir(exist_ok=True)

CONFIG_DEFAULT = {
    "current_character": "Tifa Lockhart",
}

CHARACTER_DEFAULT = {
    "system_prompt": "You are a helpful AI assistant.",
    "model": "llama3.2",
    "context_limit": 100_000,
    "temperature": 0.7,
    "conversation": [],
}
