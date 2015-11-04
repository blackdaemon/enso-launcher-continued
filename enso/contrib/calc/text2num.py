import re
import locale
import logging
import datetime
import fourfn

__all__ = ["baseN", "text2num", "format_number_local"]


def baseN(num, base, numerals="0123456789abcdefghijklmnopqrstuvwxyz"):
    """
    Convert any int to base/radix 2-36 string. Special numerals can be used
    to convert to any base or radix you need. This function is essentially
    an inverse int(s, base).

    For example:
    >>> baseN(-13, 4)
    '-31'
    >>> baseN(91321, 2)
    '10110010010111001'
    >>> baseN(791321, 36)
    'gyl5'
    >>> baseN(91321, 2, 'ab')
    'babbaabaababbbaab'
    >>> baseN(15, 16)
    'f'
    """
    if num == 0:
        return "0"

    if num < 0:
        return '-' + baseN((-1) * num, base, numerals)

    if not 2 <= base <= len(numerals):
        raise ValueError('Base must be between 2-%d' % len(numerals))

    left_digits = num // base
    if left_digits == 0:
        return numerals[num % base]
    else:
        return baseN(left_digits, base, numerals) + numerals[num % base]


def format_number_local(num):
    """
    >>> format_number_local(0)
    '0'
    >>> format_number_local(0.1)
    '0.1'
    >>> format_number_local(0.0)
    '0'
    >>> format_number_local(1024)
    '1,024'
    >>> format_number_local(1024.305)
    '1,024.305'
    >>> format_number_local(0.12300)
    '0.123'
    >>> format_number_local(1450001.1230000000000005)
    '1,450,001.123'
    >>> format_number_local(1.3)
    '1.3'
    """
    if isinstance(num, datetime.date):
        return str(num)
    elif isinstance(num, datetime.timedelta):
        return "%d days" % num.days

    try:
        long(num)
    except ValueError:
        try:
            float(num)
        except ValueError:
            return num
        except OverflowError, e:
            logging.info("%s %s" % (e[1], str(num)))
            return num
    except OverflowError, e:
        logging.info("%s %s" % (e[1], str(num)))
        return num
    except TypeError, e:
        if isinstance(num, datetime.date):
            return str(num)#num.strftime("%YY-%mm-%dd")
        elif isinstance(num, fourfn.timedelta):
            return num.expr
        elif isinstance(num, datetime.timedelta):
            return "%d days" % num.days
        else:
            return str(num)

    savelocale = locale.getlocale(locale.LC_NUMERIC)
    locale.setlocale(locale.LC_NUMERIC, "")
    #formatted = locale.str(num)
    if num % 1: # is float
        formatted = locale.format("%f", num, True)
        formatted = formatted.rstrip("0")
        if formatted.endswith("."):
            formatted = formatted + "0"
    else:
        formatted = locale.format("%d", num, True)
    locale.setlocale(locale.LC_NUMERIC, savelocale)
    return formatted


Small = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90
}

Magnitude = {
    'thousand': 1000L,
    'million': 1000L**2,
    'billion': 1000L**3,
    'trillion': 1000L**4,
    'quadrillion': 1000L**5,
    'quintillion': 1000L**6,
    'sextillion': 1000L**7,
    'septillion': 1000L**8,
    'octillion': 1000L**9,
    'nonillion': 1000L**10,
    'decillion': 1000L**11,
}

class NumberException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


def _extract_number(text):
    """
    >>> print(_extract_number(None))
    None
    >>> print(_extract_number(""))
    None
    >>> print(_extract_number("A"))
    None
    >>> print(_extract_number("0"))
    0
    >>> print(_extract_number(" - 121"))
    -121
    >>> print(_extract_number(".345"))
    0.345
    """
    if text is None:
        return None
    try:
        x = long(text)
    except ValueError:
        try:
            x = float(text)
        except ValueError:
            return None
        else:
            return x
    else:
        return x


def _convert(words):
    #print words
    n = 0
    g = None
    valid = False
    skipped_space = ""
    for idx, word in enumerate(words):
        if valid and len(word.strip(' \t')) == 0:
            skipped_space = word
            continue
        x = _extract_number(word)
        if x is not None:
            #print v
            g = (g if g is not None else 0) + x
            valid = True
            continue
        x = Small.get(word, None)
        if x is not None:
            valid = True
            g = (g if g is not None else 0) + x
            skipped_space = ""
        elif word == "hundred":
            valid = True
            g = (g if g is not None else 1) * 100
            skipped_space = ""
        else:
            x = Magnitude.get(word, None)
            if x is not None:
                valid = True
                n += (g if g is not None else 1) * x
                g = None
                skipped_space = ""
            else:
                if valid:
                    v = n + (g if g is not None else 0)
                    yield str(v), format_number_local(v)
                if skipped_space:
                    yield skipped_space, skipped_space
                    skipped_space = ""
                yield word, word
                #print words[idx:]
                for value, expr in _convert(words[idx+1:]):
                    yield value, expr
                raise StopIteration
    if valid:
        v = n + (g if g is not None else 0)
        yield str(v), format_number_local(v)


def text2num(text):
    """
    >>> text2num("four hundred fifty thousand five")
    ('450005', '450,005')
    >>> text2num("thousand")
    ('1000', '1,000')
    >>> text2num("-2 hundred sixty 5")
    ('-265', '-265')
    >>> text2num("sixty seven thousand forty one")
    ('67041', '67,041')
    >>> text2num("seventeen seven plus 12")
    ('24 plus 12', '24 plus 12')
    >>> text2num("two decillion")
    ('2000000000000000000000000000000000', '2,000,000,000,000,000,000,000,000,000,000,000')
    >>> text2num("seventeen-10.004 minus twelve")
    ('17-10.004 minus 12', '17-10.004 minus 12')
    """
    words = re.findall(r"[0-9]+(?:\.[0-9]+)?|\w+|\W+", text)
    results, formatted_results = zip(*_convert(words))
    return "".join(results), "".join(formatted_results)

# ----------------------------------------------------------------------------
# Doctests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import doctest

    doctest.testmod()

# vim:set tabstop=4 shiftwidth=4 expandtab: