import traceback

from contextlib import contextmanager


try:
    from contextlib import suppress
except ImportError:
    @contextmanager
    def suppress(*exceptions):
        """Provides the ability to not have to write try/catch blocks when just
        passing on the except.

        Thanks to Raymond Hettinger from "Transforming Code into Beautiful
        Idiotmatic Python"
        This will be included in the standard library in 3.4.

        Args:
            exceptions: A list of exceptions to ignore

        Example:

        .. code-block:: python

            # instead of...
            try:
                do_something()
            except:
                pass

            # use this:
            with suppress(Exception):
                do_something()
        """
        assert exceptions, "'exceptions' parameter in suppress() can't be empty!"
        try:
            yield
        except exceptions:
            pass

    # Deprecated
    ignored = suppress


def __do_once(ignore_args, func, *args, **kwargs):
    """ Execute the function just once """
    global __DO_ONCE_CACHE

    stack = traceback.extract_stack()
    stack.pop()
    stack.pop()
    code_location = "|".join(str(i) for i in stack.pop()[:-1])

    cache_id = "{0}|{1}|{2}".format(
        code_location,
        func,
        "|".join(str(arg) for arg in args) if not ignore_args else "",
        "|".join(kwargs.values()) if not ignore_args else "",
    )

    try:
        if cache_id in __DO_ONCE_CACHE:
            return
    except NameError:
        __DO_ONCE_CACHE = {}

    try:
        return func(*args, **kwargs)
    finally:
        __DO_ONCE_CACHE[cache_id] = 1


# TODO: Move to decorators module
def call_once(func):
    """ Function decorator. Execute the function just once,
    no matter the arguments values
    """
    def func_wrapper(*args, **kwargs):
        return __do_once(True, func, *args, **kwargs)
    return func_wrapper


def do_once(func, *args, **kwargs):
    """ Execute the function just once, no matter the arguments values """
    return __do_once(True, func, *args, **kwargs)


# TODO: Move to decorators module
def call_once_for_given_args(func):
    """ Function decorator. Execute the function just once (with given argument values).
    Using the function with different argument values will execute it again.
    """
    def func_wrapper(*args, **kwargs):
        return __do_once(False, func, *args, **kwargs)
    return func_wrapper


def do_once_for_given_args(func, *args, **kwargs):
    """ Execute the function just once (with given argument values)
    Using the function with different argument values will execute it again.
    """
    return __do_once(False, func, *args, **kwargs)

