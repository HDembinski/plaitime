from pathlib import Path

BASE_DIRECTORY = Path.home() / ".plaitime"
BASE_DIRECTORY.mkdir(exist_ok=True)
SETTINGS_FILE_NAME = BASE_DIRECTORY / "settings.json"
SESSION_DIRECTORY = BASE_DIRECTORY / "sessions"
SESSION_DIRECTORY.mkdir(exist_ok=True)
MEMORY_DIRECTORY = BASE_DIRECTORY / "memories"
MEMORY_DIRECTORY.mkdir(exist_ok=True)

CHARACTERS_PER_TOKEN = 4  # on average
