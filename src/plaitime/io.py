from pydantic import BaseModel
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging
from typing import TypeVar
from .data_models import Memory, Message
import json
from contextlib import closing

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class NoopFormatter:
    @staticmethod
    def format(x):
        return x


def save(obj: BaseModel, filename: Path):
    data = obj.model_dump_json(indent=4)
    if filename.exists():
        with open(filename, encoding="utf-8") as f:
            if data == f.read().rstrip():
                logger.info(f"no change with respect to {filename}")
                return
    with closing(
        RotatingFileHandler(
            filename, mode="w", encoding="utf-8", maxBytes=1, backupCount=10
        )
    ) as handler:
        handler.setFormatter(NoopFormatter)
        handler.emit(data)


def load(filename: Path, cls: T) -> T:
    if filename.exists():
        try:
            with open(filename, encoding="utf-8") as f:
                return cls.model_validate_json(f.read())
        except Exception as e:
            logger.error(e)

    logger.info(f"{filename} does not exist")
    return cls()
