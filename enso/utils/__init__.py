import traceback


def do_once(func, *args, **kwargs):
    """ Execute callback function just once """
    global __DO_ONCE_CACHE
    if '__DO_ONCE_CACHE' not in globals():
        __DO_ONCE_CACHE = {}
    stack = traceback.extract_stack()
    stack.pop()
    code_location = "|".join(str(i) for i in stack.pop()[:-1])
    # print code_location
    if code_location not in __DO_ONCE_CACHE:
        try:
            func(*args, **kwargs)
        finally:
            __DO_ONCE_CACHE[code_location] = 1

call_once = do_once
