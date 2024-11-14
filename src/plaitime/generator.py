import ollama
from PySide6 import QtCore
import logging
from . import MODEL_TIMEOUT
from typing import Generator

logger = logging.getLogger(__name__)


class GeneratorThread(QtCore.QThread):
    interrupt: bool = False
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(
        self,
        model: str,
        options: dict[str, str | int | float],
        payload: str | list[dict[str, str]],
    ):
        super().__init__()
        self.model = model
        self.options = options
        self.payload = payload

    def run(self):
        try:
            for response in self._generator():
                if self.interrupt:
                    return
                chunk = response["message"]["content"]
                self.nextChunk.emit(chunk)
        except Exception as e:
            error_message = f"""Error generating response: {str(e)}\n\n
Please make sure that the model '{self.model}' is available.
You can run 'ollama run {self.model}' in terminal to check."""
            self.error.emit(error_message)

    def _generator(self) -> Generator:
        NotImplemented


class Chat(GeneratorThread):
    def __init__(
        self,
        model: str,
        messages: list[dict[str, str]],
        **options: dict[str, str | int | float],
    ):
        super().__init__(model, options, messages)

    def _generator(self):
        yield from ollama.chat(
            model=self.model,
            messages=self.payload,
            stream=True,
            keep_alive=MODEL_TIMEOUT,
            options=self.options,
        )


class Generate(GeneratorThread):
    def __init__(
        self,
        model: str,
        prompt: str,
        **options: dict[str, str | int | float],
    ):
        super().__init__(model, options, prompt)

    def _generator(self):
        yield from ollama.generate(
            model=self.model,
            prompt=self.payload,
            stream=True,
            keep_alive=MODEL_TIMEOUT,
            options=self.options,
        )
