import logging


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


def set_logging(production: bool = True):
    global _logger
    if production:
        _logger = NullLogger()
    else:
        _logger = logging.getLogger()
        _logger.setLevel(logging.INFO)

        if not _logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            _logger.addHandler(handler)

def get_logger():
    global _logger
    return _logger
