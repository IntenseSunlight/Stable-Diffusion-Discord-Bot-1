import logging


class LogOnce:
    _instance = None

    def __call__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance

    def __init__(self, logger: logging.Logger = logging):
        self._logger = logger
        self._have_logged = set()

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        if msg not in self._have_logged:
            self._have_logged.add(msg)
            self._logger.warn(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
