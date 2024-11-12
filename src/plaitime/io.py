from pydantic import BaseModel
from pathlib import Path
from logging.handlers import RotatingFileHandler
import logging
from typing import TypeVar
from contextlib import closing

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


def save(obj: BaseModel, filename: Path):
    data = obj.model_dump_json(indent=4)
    if filename.exists():
        with open(filename, encoding="utf-8") as f:
            if data == f.read().rstrip():
                logger.info(f"no change with respect to {filename}")
                return
    with closing(
        RotatingFileHandler(
            filename, mode="w", encoding="utf-8", maxBytes=1, backupCount=9
        )
    ) as handler:
        record = logging.makeLogRecord({"msg": data})
        handler.emit(record)


def load(filename: Path, cls: T) -> T:
    try:
        with open(filename, encoding="utf-8") as f:
            return cls.model_validate_json(f.read())
    except Exception as e:
        logger.error(e)
        return cls()
