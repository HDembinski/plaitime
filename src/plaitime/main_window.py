import logging

import ollama
from ollama import ResponseError
from PySide6 import QtCore, QtGui, QtWidgets

from . import (
    CHARACTER_DIRECTORY,
    CONFIG_FILE_NAME,
    MEMORY_DIRECTORY,
    STORY_EXTRACTION_PROMPT,
    CONTEXT_MARGIN_FRACTION,
    CHARACTERS_PER_TOKEN,
)
from .character_bar import CharacterBar
from .config_dialog import ConfigDialog
from .data_models import Character, Config, Memory, Message
from .generator import Chat, Generate, GeneratorThread
from .chat_widget import ChatWidget
from .util import estimate_num_tokens
from .io import load, save, lock_and_load, save_and_release, rename
from uuid import uuid4

logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    character: Character
    generator: GeneratorThread | None
    cancel_mode: str

    def __init__(self):
        super().__init__()
        self.character = Character()
        self.generator = None
        self.cancel_mode = "rewind"
        self.uid = str(uuid4())

        self.setWindowTitle("Plaitime")
        self.setMinimumSize(600, 500)

        # Create top bar
        self.character_bar = CharacterBar()
        self.setMenuWidget(self.character_bar)
        self.character_bar.config_button.clicked.connect(self.show_config_dialog)
        self.character_bar.new_button.clicked.connect(self.new_character)
        self.character_bar.summary_button.clicked.connect(self.generate_summary)
        self.character_bar.character_selector.currentTextChanged.connect(
            self.switch_character
        )
        self.character_bar.clipboard_button.clicked.connect(self.copy_to_clipboard)

        self.chat_widget = ChatWidget(self)
        self.chat_widget.sendMessage.connect(self.generate_response)
        self.setCentralWidget(self.chat_widget)

        # Must be at the end
        config = self.load_config()
        self.load_character(config.current_character)

    def load_messages(self, prompt: str, memory: Memory):
        self.chat_widget.clear()
        self.chat_widget.setUpdatesEnabled(False)

        messages = memory.messages
        if messages and messages[-1].role == "user":
            m = messages.pop()
            self.chat_widget.set_input_text(m.content)
        for m in messages:
            self.chat_widget.add(m.role, m.content)

        self.chat_widget.setUpdatesEnabled(True)

        num_token = estimate_num_tokens(prompt, messages)
        self.character_bar.update_num_token(num_token, self.context_size)

    def load_config(self) -> Config:
        return load(CONFIG_FILE_NAME, Config)

    def save_config(self):
        config = Config(current_character=self.character_bar.current_character())
        save(config, CONFIG_FILE_NAME)

    def load_character(self, name: str):
        names = get_character_names()
        if not name and names:
            name = names[0]
        try:
            self.character = lock_and_load(
                CHARACTER_DIRECTORY / f"{name}.json", Character, self.uid
            )
        except IOError:
            self.load_character("")
            return
        self.warmup_model()
        self.character_bar.set_character_manually(names, self.character.name)
        self.context_size = get_context_size(self.character.model)
        if self.character.save_conversation:
            memory = load(MEMORY_DIRECTORY / f"{name}.json", Memory)
        else:
            memory = Memory()
        self.load_messages(self.character.prompt, memory)

    def save_character(self):
        c = self.character
        logger.info(f"saving character {c.name}")
        try:
            save_and_release(c, CHARACTER_DIRECTORY / f"{c.name}.json", self.uid)
        except ValueError:
            logger.warning("cannot save character which is locked by another instance")
            return

        if c.save_conversation:
            widgets = self.chat_widget.get_messages()
            messages = [Message(role=w.role, content=w.content) for w in widgets]
            user_text = self.chat_widget.get_user_text()
            if user_text:
                messages.append(Message(role="user", content=user_text))
            if messages:
                memory = Memory(messages=messages)
                save(memory, MEMORY_DIRECTORY / f"{c.name}.json")
                return
        # remove file, if there is nothing to save
        path = MEMORY_DIRECTORY / f"{c.name}.json"
        path.unlink(missing_ok=True)

    def delete_character(self, name: str):
        logger.info(f"deleting character {name}")
        for path in (
            CHARACTER_DIRECTORY / f"{name}.json",
            CHARACTER_DIRECTORY / f"{name}.lock",
            MEMORY_DIRECTORY / f"{name}.json",
        ):
            path.unlink(missing_ok=True)

    def rename_character(self, old_name: str, new_name: str):
        logger.info(f"renaming character from {old_name!r} to {new_name!r}")
        files = [
            CHARACTER_DIRECTORY / f"{old_name}.json",
            CHARACTER_DIRECTORY / f"{old_name}.lock",
            MEMORY_DIRECTORY / f"{old_name}.json",
        ]
        for f in files:
            if f.exists():
                rename(f, new_name)

    def save_all(self):
        self.save_config()
        self.save_character()

    def show_config_dialog(self):
        widgets = self.chat_widget.get_messages()
        messages = []
        for w in widgets:
            messages.append(Message(role=w.role, content=w.content))
        self.configure_character(self.character, Memory(messages=messages))

    def configure_character(self, character: Character, memory: Memory):
        dialog = ConfigDialog(character.model_copy(), memory.model_copy(), parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            r: str | tuple[Character, Memory] = dialog.result()
            if isinstance(r, str):
                self.delete_character(r)
                self.load_character("")
            else:
                character, memory = r
                if self.character.name != character.name:
                    self.rename_character(self.character.name, character.name)
                self.character = character
                names = get_character_names()
                self.character_bar.set_character_manually(names, character.name)
                self.context_size = get_context_size(self.character.model)
                self.load_messages(character.prompt, memory)

    def new_character(self):
        self.save_character()
        # this is important, otherwise the old character is deleted in configure_character
        self.character = Character()
        self.memory = Memory()
        self.configure_character(self.character, self.memory)
        names = get_character_names()
        self.character_bar.set_character_manually(names, self.character.name)

    def switch_character(self, name):
        logger.info(f"switching character to {name}")
        self.save_character()
        self.load_character(name)

    def rewind(self, partial=True):
        self.cancel_generator()
        if self.cancel_mode == "rewind":
            self.chat_widget.rewind(partial)

    def generator_finished(self):
        self.chat_widget.enable()
        self.generator = None
        num_token = estimate_num_tokens(
            self.character.prompt, self.chat_widget.get_messages()
        )
        self.character_bar.update_num_token(num_token, self.context_size)

    def generate_response(self):
        self.chat_widget.disable()
        self.save_character()

        prompt = self.character.prompt

        # enable endless chatting by clipping the part of the conversation
        # that the llm can see, but keep the system prompt at all times
        window = []
        num_token = len(prompt) / CHARACTERS_PER_TOKEN
        for w in reversed(self.chat_widget.get_messages()):
            w.unmark()
            window.append({"role": w.role, "content": w.content})
            num_token += len(w.content) / CHARACTERS_PER_TOKEN
            if num_token > self.context_size * (1 - CONTEXT_MARGIN_FRACTION):
                break
        assert len(window) > 0
        assert w.content == window[-1]["content"]
        w.mark()
        window.append({"role": "system", "content": prompt})
        window.reverse()

        self.cancel_generator(wait=True)
        self.generator = Chat(
            self.character.model, window, temperature=self.character.temperature
        )
        mw = self.chat_widget.add("assistant", "")
        self.generator.nextChunk.connect(mw.add_chunk)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generator_finished)
        self.cancel_mode = "rewind"
        self.generator.start()

    def get_dialog_as_text(self):
        messages = self.chat_widget.get_messages()
        text = self.character.prompt + "\n\n".join(
            f"{m.role.capitalize()}:\n{m.content}" for m in messages
        )
        return text

    def copy_to_clipboard(self):
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(self.get_dialog_as_text())

    def generate_summary(self):
        prompt = STORY_EXTRACTION_PROMPT.format(self.get_dialog_as_text())
        logger.info(prompt)

        self.cancel_generator(wait=True)
        self.cancel_mode = "cancel"
        self.generator = Generate(
            self.character.model,
            prompt=prompt,
            temperature=0.1,
        )
        self.generator.nextChunk.connect(self.chat_widget.append_user_text)
        self.generator.error.connect(self.show_error_message)
        self.generator.finished.connect(self.generate_summary_finished)
        self.generator.start()

    def show_error_message(self, message: str):
        msg = QtWidgets.QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()

    def generate_summary_finished(self):
        self.generator = None
        self.chat_widget.enable()

    def cancel_generator(self, *, wait=False):
        self.cancel_mode = "rewind"
        if self.generator and self.generator.isRunning():
            logger.info("Generator is running, interrupting...")
            self.generator.interrupt = True
            if wait:
                logger.info("Waiting for generator to finish...")
                self.generator.wait()
                self.generator = None

    def keyPressEvent(self, event):
        key = event.key()
        mod = event.modifiers()
        if key == QtCore.Qt.Key_Escape:
            self.rewind(not (mod & QtCore.Qt.KeyboardModifier.ShiftModifier))
        elif key == QtCore.Qt.Key_Return:
            self.chat_widget.keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def warmup_model(self):
        self.cancel_generator(wait=True)
        self.generator = Generate(self.character.model, "")

        def finished():
            self.generator = None

        self.generator.finished.connect(finished)
        self.generator.start()


def get_context_size(model):
    try:
        d = ollama.show(model)["model_info"]
        for key in d:
            if "context_length" in key:
                return d[key]
        raise RuntimeError("context_length not found")
        # model was removed
    except ResponseError:
        return 0


def get_character_names():
    names = []
    for fname in CHARACTER_DIRECTORY.glob("*.json"):
        names.append(fname.stem)
    return names
