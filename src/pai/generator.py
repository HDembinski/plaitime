import ollama as llm
from PySide6 import QtCore
from pai import CONTEXT_MARGIN, CHARACTERS_PER_TOKEN


class Generator(QtCore.QThread):
    increment = QtCore.Signal(str)
    error = QtCore.Signal(str)

    def __init__(self, character, messages, context_size):
        super().__init__()
        self.character = character
        self.messages = messages
        self.context_size = context_size
        self.interrupt = False

    def run(self):
        # we always use current system prompt
        system_prompt = self.character.prompt or "You are a helpful AI assistant."
        messages = self.messages

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        conversation_window = []
        num_token = len(system_prompt) / CHARACTERS_PER_TOKEN
        i = len(messages) - 1
        while num_token < self.context_size - CONTEXT_MARGIN and i >= 0:
            message = messages[i]
            conversation_window.append(message.dict())
            i -= 1
            num_token += len(message.content) / CHARACTERS_PER_TOKEN
        conversation_window.append({"role": "system", "content": system_prompt})
        conversation_window.reverse()

        if len(conversation_window) >= 2:
            for which, idx in zip(
                ("first", "second", "second to last", "last"), (0, 1, -2, -1)
            ):
                message = conversation_window[idx]
                print(which)
                print(message["role"])
                print(message["content"])
                print("---")

        try:
            # Generate streaming response using Ollama
            for response in llm.chat(
                model=self.character.model,
                messages=conversation_window,
                stream=True,
                options={"temperature": self.character.temperature},
            ):
                if self.interrupt:
                    break
                self.increment.emit(response["message"]["content"])
        except Exception as e:
            error_message = f"""Error generating response: {str(e)}\n\n
Please make sure that the model '{self.character.model}' is available.
You can run 'ollama run {self.character.model}' in terminal to check."""
            self.error.emit(error_message)
