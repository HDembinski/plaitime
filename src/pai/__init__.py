from pathlib import Path

CONFIG_FILE_NAME = Path.home() / ".pai.cfg"
CONFIG_DEFAULT = {
    "system_prompt": "You are a helpful AI assistant.",
    "temperature": 0.7,
    "model_name": "llama3.2",
}
