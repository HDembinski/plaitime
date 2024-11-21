import ollama
from PySide6 import QtCore
import logging
from typing import Generator
from .data_models import Message

logger = logging.getLogger(__name__)


class GeneratorThread(QtCore.QThread):
    interrupt: bool = False
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(
        self,
        model: str,
        keep_alive: str,
        options: dict[str, str | int | float],
        payload: str | list[dict[str, str]],
    ):
        super().__init__()
        self.model = model
        self.keep_alive = keep_alive
        self.options = options
        self.payload = payload

    def run(self):
        try:
            for response in self._generator():
                if self.interrupt:
                    return
                if "message" in response:
                    chunk = response["message"]["content"]
                else:
                    chunk = response["response"]
                self.nextChunk.emit(chunk)
        except Exception:
            import traceback

            error = traceback.format_exc(chain=False)

            error_message = f"""Error generating response{error}\n
Please make sure that the model '{self.model}' is available.
You can run 'ollama run {self.model}' in terminal to check."""
            self.error.emit(error_message)

    def _kwargs(self):
        return {
            "model": self.model,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": self.options,
        }

    def _generator(self) -> Generator:
        NotImplemented


class Chat(GeneratorThread):
    def __init__(
        self,
        model: str,
        messages: list[Message],
        keep_alive: str,
        **options: dict[str, str | int | float],
    ):
        super().__init__(
            model,
            keep_alive,
            options,
            [{"role": m.role, "content": m.content} for m in messages],
        )

    def _generator(self):
        yield from ollama.chat(**self._kwargs(), messages=self.payload)


class Generate(GeneratorThread):
    def __init__(
        self,
        model: str,
        prompt: str,
        keep_alive: str,
        **options: dict[str, str | int | float],
    ):
        super().__init__(model, keep_alive, options, prompt)

    def _generator(self):
        yield from ollama.generate(**self._kwargs(), prompt=self.payload)


class GenerateJson(GeneratorThread):
    def __init__(
        self,
        model: str,
        prompt: str,
        keep_alive: str,
        **options: dict[str, str | int | float],
    ):
        super().__init__(model, keep_alive, options, prompt)

    def _generator(self):
        yield from ollama.generate(**self._kwargs(), prompt=self.payload)
