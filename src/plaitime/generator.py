import ollama
from PySide6 import QtCore
import logging

logger = logging.getLogger(__name__)


class Generator(QtCore.QThread):
    interrupt: bool = False
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(
        self,
        model: str,
        messages: list[dict[str, str]],
        **options: dict[str, str | int | float],
    ):
        super().__init__()
        self.model = model
        self.messages = messages
        self.options = options

    def run(self):
        try:
            for response in ollama.chat(
                model=self.model,
                messages=self.messages,
                stream=True,
                options=self.options,
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
