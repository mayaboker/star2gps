
DATA_FORMAT = "<ddd" # lat, lon, alt as doubles as little-endian

class SingletonMeta(type):
    """ A thread-safe implementation of Singleton.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Event:
    """
    Simple event container. Use `event += handler` to register handlers
    and `event.fire(*args, **kwargs)` to call them.
    """
    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler):
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers.append(handler)
        return self



    def fire(self, *args, **kwargs):
        """Invoke all registered handlers with the given arguments.
        #TODO: what about exception handling here?
        """
        for handler in list(self._handlers):
            handler(*args, **kwargs)
