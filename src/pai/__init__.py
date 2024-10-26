from pathlib import Path

BASE_DIRECTORY = Path.home() / ".pai"
BASE_DIRECTORY.mkdir(exist_ok=True)

CONFIG_FILE_NAME = BASE_DIRECTORY / "pai.json"
CHARACTER_DIRECTORY = BASE_DIRECTORY / "characters"
CHARACTER_DIRECTORY.mkdir(exist_ok=True)

CONFIG_DEFAULT = {
    "current_character": "Assistant",
    "general_prompt": "Use Markdown in your responses. When you describe actions, use the third-person for yourself and italic markup. Example: *{name} smiles and winks at you* Hi, I am {name}!",
}

CHARACTER_DEFAULT = {
    "prompt": "You are a helpful AI assistant.",
    "model": "llama3.2",
    "temperature": 0.7,
    "conversation": [],
}
