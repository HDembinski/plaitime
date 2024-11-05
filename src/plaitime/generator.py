import ollama
from PySide6 import QtCore
import logging

logger = logging.getLogger(__name__)


class Generator(QtCore.QThread):
    interrupt: bool = False
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, model: str, temperature: float, messages: list[dict[str, str]]):
        super().__init__()
        self.model = model
        self.temperature = temperature
        self.messages = messages

    def run(self):
        try:
            for response in ollama.chat(
                model=self.model,
                messages=self.messages,
                stream=True,
                options={"temperature": self.temperature},
            ):
                if self.interrupt:
                    return
                chunk = response["message"]["content"]
                self.nextChunk.emit(chunk)
        except Exception as e:
            error_message = f"""Error generating response: {str(e)}\n\n
Please make sure that the model '{self.model}' is available.
You can run 'ollama run {self.model}' in terminal to check."""
            self.error.emit(error_message)
