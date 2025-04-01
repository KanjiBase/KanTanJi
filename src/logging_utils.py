import logging
from pathlib import Path


class NullLogger:
    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def warn(self, *args, **kwargs):  # for compatibility with older logging
        pass

    def error(self, *args, **kwargs):
        pass

    def critical(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass

    def log(self, *args, **kwargs):
        pass

    def setLevel(self, *args, **kwargs):
        pass

    def addHandler(self, *args, **kwargs):
        pass

    def removeHandler(self, *args, **kwargs):
        pass


_logger = None


def set_logging(production: bool = True, output_file: str = None):
    global _logger
    if production:
        _logger = NullLogger()
    else:
        _logger = logging.getLogger("kantanji")
        _logger.setLevel(logging.INFO)

        if output_file is None:
            if not _logger.hasHandlers():
                handler = logging.StreamHandler()
                handler.setLevel(logging.INFO)
                formatter = logging.Formatter("[%(levelname)s] %(message)s")
                handler.setFormatter(formatter)
                _logger.addHandler(handler)
        else:
            formatter = logging.Formatter("[%(levelname)s] %(message)s")

            # Console handler
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            _logger.addHandler(stream_handler)

            # File handler
            log_file = Path(output_file)
            file_handler = logging.FileHandler(log_file, mode="w")
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)

def get_logger():
    global _logger
    return _logger

