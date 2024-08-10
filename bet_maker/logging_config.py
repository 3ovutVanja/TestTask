import os
from logging.config import dictConfig

logs_dir = "/storage/logs"
os.makedirs(logs_dir, exist_ok=True)
log_filename = os.path.join(logs_dir, "bet_maker.log")

level = "DEBUG"


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format":
                '%(asctime)s - %(levelname)s - [%(name)s] - [%(filename)s : %(funcName)s : %(lineno)d] - %(message)s',
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
    },
    "handlers": {
        "file": {
            "level": level,
            "class": "logging.FileHandler",
            "filename": log_filename,
            "formatter": "default"
        },
        "console": {
            "level": level,
            "class": "logging.StreamHandler",
            "formatter": "default"
        },
    },
    "loggers": {
        "": {
            "handlers": ["file", "console"],
            "level": level,
            "propagate": True
        },
        "fastapi": {
            "handlers": ["file", "console"],
            "level": level,
            "propagate": False
        },
        "tortoise": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["file", "console"],
            "level": level,
            "propagate": False
        },
    }
}


def setup_logging():
    with open(log_filename, 'w'):
        pass
    dictConfig(logging_config)
