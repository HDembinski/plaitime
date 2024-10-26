from pathlib import Path

CONFIG_FILE_NAME = Path.home() / ".pai.cfg"
CONFIG_DEFAULT = {
    "system_prompt": "You are a helpful AI assistant.",
    "model": "llama3.2",
    "context_limit": 100_000,
    "temperature": 0.7,
    "conversation": [],
}
