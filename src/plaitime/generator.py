import ollama
from PySide6 import QtCore
from . import CONTEXT_MARGIN, CHARACTERS_PER_TOKEN
from .message_widget import MessageWidget
import logging

logger = logging.getLogger(__name__)


class Generator(QtCore.QThread):
    interrupt: bool = False
    nextChunk = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(
        self,
        model: str,
        temperature: float,
        prompt: str,
        widgets: list[MessageWidget],
        context_size: int,
    ):
        super().__init__()
        self.model = model
        self.prompt = prompt or "You are a helpful AI assistant."
        self.temperature = temperature
        self.widgets = widgets
        self.context_size = context_size

    def run(self):
        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        conversation_window = []
        num_token = len(self.prompt) / CHARACTERS_PER_TOKEN
        for w in reversed(self.widgets):
            num_token += len(w.content) / CHARACTERS_PER_TOKEN
            if num_token > self.context_size - CONTEXT_MARGIN:
                break
            conversation_window.append(w.dict())
        conversation_window.append({"role": "system", "content": self.prompt})
        conversation_window.reverse()

        try:
            for response in ollama.chat(
                model=self.model,
                messages=conversation_window,
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
