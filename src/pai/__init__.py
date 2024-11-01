from pathlib import Path

BASE_DIRECTORY = Path.home() / ".pai"
BASE_DIRECTORY.mkdir(exist_ok=True)

CONFIG_FILE_NAME = BASE_DIRECTORY / "pai.json"
CHARACTER_DIRECTORY = BASE_DIRECTORY / "characters"
CHARACTER_DIRECTORY.mkdir(exist_ok=True)
MEMORY_DIRECTORY = BASE_DIRECTORY / "memories"
MEMORY_DIRECTORY.mkdir(exist_ok=True)

CHARACTERS_PER_TOKEN = 4  # on average
CONTEXT_MARGIN = 512
