# -*- coding: utf-8 -*-
# vim:set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
#
# fourFn.py
#
# Demonstration of the pyparsing module, implementing a simple 4-function
# expression parser, with support for scientific notation, and symbols
# for e and pi. Extended to add exponentiation and simple built-in functions.
# Extended test cases, simplified pushFirst method.
#
# Copyright (c) 2003-2006 by Paul McGuire

# Author : Pavel Vitis "blackdaemon"
# Email  : blackdaemon@seznam.cz
#
# Copyright (c) 2010, Pavel Vitis <blackdaemon@seznam.cz>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#    3. Neither the name of Enso nor the names of its contributors may
#       be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

from __future__ import division
import datetime
import math
import operator
import re

import pyparsing
from enso.contrib.calc.exchangerates.converter import (
    get_currency_rates,
    get_home_currency,
    convert_currency
)

from dateutil.relativedelta import relativedelta
from pyparsing import (
    CaselessLiteral,
    Combine,
    Forward,
    Literal,
    OneOrMore,
    Optional,
    ParseResults,
    Word,
    ZeroOrMore,
    oneOf,
    alphas,
    nums,
)
from text2num import text2num

__updated__ = "2018-06-22"
__all__ = ["evaluate"]

RE_ROMAN_NUMERALS = '[IVXLCDMivxlcdm]+'
RE_VALID_ROMAN_NUMBER = r"\b(M{0,4}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\b"

RE_TIMEDELTA = r"(\d+) ?(days?|weeks?|months?|years?)"


class timedelta(relativedelta):

    def __init__(self, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0, microseconds=0):
        super(timedelta, self).__init__(
            days=days,
            seconds=seconds,
            microseconds=microseconds,
            minutes=minutes,
            hours=hours,
            weeks=weeks,
            months=months,
            years=years)

        self.expr = "".join((
            "%d days " % days if days != 0 else "",
            "%d weeks " % weeks if weeks != 0 else "",
            "%d months " % months if months != 0 else "",
            "%d years " % years if years != 0 else ""
        ))
        if not self.expr:
            self.expr = "0 days"


class Regex(pyparsing.Regex):

    def parseImpl(self, instring, loc, doActions=True):
        result = self.re.match(instring, loc)
        if not result or len(result.groups()) == 0 or len("".join(result.groups())) == 0:
            raise pyparsing.ParseException(instring, loc, self.errmsg, self)

        loc = result.end()
        d = result.groupdict()
        ret = ParseResults(result.group())
        if d:
            for k in d:
                ret[k] = d[k]
        return loc, ret


class BNF(object):
    """
    """
    __bnf = None
    expr_stack = []

    @classmethod
    def invalidate(cls):
        cls.__bnf = None

    @classmethod
    def pushFirst(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy
        cls.expr_stack.append(toks[0])

    @classmethod
    def pushSecond(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy
        cls.expr_stack.append(toks[1])

    @classmethod
    def pushUMinus(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy
        if toks:
            if toks[0] == '-':
                cls.expr_stack.append('unary -')
                #~ exprStack.append( '-1' )
                #~ exprStack.append( '*' )
            if toks[0] == '(' and toks[-1] == ')':
                cls.expr_stack.append("()")
                #~ exprStack.append( '-1' )
                #~ exprStack.append( '*' )

    @classmethod
    def pushFunc(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy
        cls.expr_stack.append(toks[1])
        return ParseResults([toks[0]])

    @classmethod
    def pushCurrency(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy
        if len(cls.expr_stack[-1]) == 3:
            # Only source currency specified, add home currency as target
            cls.expr_stack.append(get_home_currency())
        elif len(cls.expr_stack[-1]) == 6:
            # Split source and target currency on stack
            cls.expr_stack.append(cls.expr_stack[-1][3:])
            cls.expr_stack[-2] = cls.expr_stack[-2][:3]
        cls.expr_stack.append("currency")

    @classmethod
    def pushNumber(cls, strg, loc, toks):
        _, _ = loc, strg  # keep pylint happy

    @classmethod
    def get_bnf(cls):
        """
        expop   :: '^' | '**'
        multop  :: '*' | '/' | '//' | '%'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: real squared | PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        if cls.__bnf is None:
            point = Literal(".")
            thousands_separator = Literal(",").suppress()
            e = CaselessLiteral("E")

            inumber = Combine(
                Optional(oneOf("+", "-")) +
                (
                    # Format with thousands separators
                    Word(nums, min=1, max=3) + \
                    ZeroOrMore(
                        Combine(thousands_separator + Word(nums, min=3, max=3)))
                    # Format without thousands separators
                    | Word(nums)
                )
            ).setParseAction(cls.pushNumber)
            # Regex("[0-9]{1,3}(,[0-9]{3})*").setParseAction(cls.pushNumber)
            fnumber = Combine(inumber +
                              Optional(point + Optional(Word(nums))) +
                              Optional(e + Word("+-" + nums, nums)))

            roman_numerals = Regex(RE_VALID_ROMAN_NUMBER, re.IGNORECASE).setParseAction(
                lambda s, l, t: [str(roman_to_int(t[0]))])

            ident = Word(alphas, alphas + nums + "_$")

            plus = Literal(
                "+") | CaselessLiteral("plus") | CaselessLiteral("add")
            minus = Literal("-") | CaselessLiteral("minus") | CaselessLiteral(
                "substract") | CaselessLiteral("subtract") | CaselessLiteral("sub")
            mult = Literal("*") | CaselessLiteral("times") | CaselessLiteral(
                "multiplied by") | CaselessLiteral("multiply") | CaselessLiteral("mul")
            div = Literal(
                "/") | CaselessLiteral("divided by") | CaselessLiteral("divide") | CaselessLiteral("div")
            floor = Literal("//") | CaselessLiteral("floor")
            mod = Literal("%") | CaselessLiteral(
                "modulo") | CaselessLiteral("mod")
            lpar = Literal("(")  # .suppress()
            rpar = Literal(")")  # .suppress()
            addop = plus | minus
            multop = mult | floor | div | mod
            expop = Literal("^") | Literal(
                "**") | CaselessLiteral("power") | CaselessLiteral("pow")
            pi = CaselessLiteral("PI")
            bitwise = CaselessLiteral("xor") | CaselessLiteral(
                "and") | CaselessLiteral("or")
            currencyop = CaselessLiteral("in")
            shift = Literal("<<") | Literal(">>")

            now = CaselessLiteral("now").setParseAction(
                lambda s, l, t: [datetime.datetime.now()])
            one_day = timedelta(days=1)
            today = CaselessLiteral("today").setParseAction(
                lambda s, l, t: [datetime.date.today()])
            yesterday = CaselessLiteral("yesterday").setParseAction(
                lambda s, l, t: [datetime.date.today() - one_day])
            tomorrow = CaselessLiteral("tomorrow").setParseAction(
                lambda s, l, t: [datetime.date.today() + one_day])
            minutes = Combine(
                (Word("+-" + nums, nums) +
                 CaselessLiteral("minutes").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("minute").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(minutes=long(t[0]))])
            hours = Combine(
                (Word("+-" + nums, nums) + CaselessLiteral("hours").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("hour").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(hours=long(t[0]))])
            days = Combine(
                (Word("+-" + nums, nums) + CaselessLiteral("days").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("day").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(days=long(t[0]))])
            weeks = Combine(
                (Word("+-" + nums, nums) + CaselessLiteral("weeks").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("week").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(weeks=long(t[0]))])
            months = Combine(
                (Word("+-" + nums, nums) +
                 CaselessLiteral("months").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("month").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(months=long(t[0]))])
            years = Combine(
                (Word("+-" + nums, nums) + CaselessLiteral("years").suppress())
                | (Optional(Word("+-" + nums, nums), "1") + CaselessLiteral("year").suppress())
            ).setParseAction(lambda s, l, t: [timedelta(years=long(t[0]))])
            date = Combine(
                Word(nums) + Literal(".") + Word(nums) + Literal(".") +
                Optional(Word(nums), datetime.date.today().year)
            ).setParseAction(lambda s, l, t: [datetime.datetime.strptime(t[0], "%d.%m.%Y").date()])

            currency_name = Word(alphas, min=3, max=3)
            currency_pair = Word(alphas, min=6, max=6)
            """
            currency_name = Forward()
            for cur_code in get_currency_rates().exchange_rates.keys():
                currency_name |= CaselessLiteral(cur_code)
            """
            currency_name.setParseAction(cls.pushFirst)
            currency_pair.setParseAction(cls.pushFirst)
            # print currency_name

            expr = Forward()
            atom = (Optional("-") + (now | date | today | yesterday | tomorrow | hours | minutes
                                     | days | weeks | months | years | pi | e | fnumber | roman_numerals | ident + lpar + expr + rpar).setParseAction(cls.pushFirst)
                    | (lpar + expr + rpar)).setParseAction(cls.pushUMinus)
#                 | ( lpar + expr.suppress() + rpar )).setParseAction(cls.pushUMinus)

            # by defining exponentiation as "atom [ ^ factor ]..." instead of "atom [ ^ atom ]...",
            # we get right-to-left exponents, instead of left-to-right, that
            # is, 2^3^2 = 2^(3^2), not (2^3)^2.
            factor = Forward()
            factor << atom + \
                ZeroOrMore((expop + factor).setParseAction(cls.pushFirst))

            term = factor + \
                ZeroOrMore((multop + factor).setParseAction(cls.pushFirst))
            expr << term + \
                ZeroOrMore(
                    ((addop | bitwise | shift) + term).setParseAction(cls.pushFirst))

            # currency_value = Combine(
            #    ( expr ).setParseAction( cls.pushFirst ) +
            #    currency_name,
            #    adjacent = False )

            expr1 = expr + \
                Optional(
                    (currency_name | currency_pair).setParseAction(cls.pushCurrency))

            # print expr1
            cls.__bnf = expr1
        return cls.__bnf


roman_numeral_map = zip(
    (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
    ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
)


def int_to_roman(i):
    result = []
    for integer, numeral in roman_numeral_map:
        count = int(i / integer)
        result.append(numeral * count)
        i -= integer * count
    return ''.join(result)


def roman_to_int(n):
    n = unicode(n).upper()

    i = result = 0L
    for integer, numeral in roman_numeral_map:
        while n[i:i + len(numeral)] == numeral:
            result += integer
            i += len(numeral)
    return result


# map operator symbols to corresponding arithmetic operations
epsilon = 1e-12

opn = {
    "+": operator.add,
    "plus": operator.add,
    "add": operator.add,

    "-": operator.sub,
    "minus": operator.sub,
    "substract": operator.sub,
    "subtract": operator.sub,
    "sub": operator.sub,

    "*": operator.mul,
    "times": operator.mul,
    "multiplied by": operator.mul,
    "multiply": operator.mul,
    "mul": operator.mul,

    "/": operator.truediv,
    "divided by": operator.truediv,
    "divide": operator.truediv,
    "div": operator.truediv,

    "//": operator.floordiv,
    "floor": operator.floordiv,

    "%": operator.mod,
    "modulo": operator.mod,
    "mod": operator.mod,

    "^": operator.pow,
    "**": operator.pow,
    "pow": operator.pow,
    "power": operator.pow,

    "and": operator.and_,
    "or": operator.or_,
    "xor": operator.xor,

    ">>": operator.rshift,
    "<<": operator.lshift,
}

fn = {"sin": math.sin,
      "cos": math.cos,
      "tan": math.tan,
      "asin": math.asin,
      "acos": math.acos,
      "atan": math.atan,
      "acosh": math.acosh,
      "asinh": math.asinh,
      "atanh": math.atanh,
      "cosh": math.cosh,
      "sinh": math.sinh,
      "tanh": math.tanh,
      "rad": math.radians,
      "deg": math.degrees,
      "abs": abs,
      "sqrt": math.sqrt,
      "trunc": lambda a: long(a),
      "round": round,
      "squared": lambda x: x * x,
      "cubed": lambda x: x * x * x,
      "sgn": lambda a: 0 if a == 0 else 1 if abs(a) > epsilon and cmp(a, 0) > 0 else -1,
      "invert": operator.invert,
      "~": operator.invert,
      "currency": convert_currency
      }


def evaluateStack(s):
    op = s.pop()
    # print op

    if isinstance(op, datetime.datetime):
        return op, op.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(op, datetime.date):
        return op, str(op)
    elif isinstance(op, datetime.time):
        return op, str(op)
    elif isinstance(op, timedelta):
        return op, str(op)

    if op == 'unary -':
        val, expr = evaluateStack(s)
        val = -val
        return val, "-%s" % expr
    elif op in set(["xor", "and", "or"]):
        op2, expr2 = evaluateStack(s)
        op1, expr1 = evaluateStack(s)
        val = opn[op](long(op1), long(op2))
        print op, opn[op]
        return val, "%s %s %s" % (expr1, op, expr2)
    elif op in set([
            "+", "plus", "add",
            "-", "minus", "substract", "subtract", "sub",
            "*", "times", "multiplied by", "multiply", "mul",
            "pow", "power", "**", "^",
            ">>", "<<"]):
        op2, expr2 = evaluateStack(s)
        op1, expr1 = evaluateStack(s)
        if isinstance(op1, datetime.datetime):
            if isinstance(op2, long):
                op2 = timedelta(hours=op2)
                expr2 = op2.expr
        elif isinstance(op1, datetime.date):
            if isinstance(op2, long):
                op2 = timedelta(days=op2)
                expr2 = op2.expr
            elif isinstance(op2, timedelta):
                pass
            else:
                return "undefined", "%s %s %s" % (expr1, op.strip(), expr2)
        elif isinstance(op2, datetime.date):
            if isinstance(op1, long):
                op1 = timedelta(days=op1)
                expr1 = op1.expr
            elif isinstance(op1, timedelta):
                pass
            else:
                return "undefined", "%s %s %s" % (expr1, op.strip(), expr2)
        val = opn[op](op1, op2)
        return val, "%s %s %s" % (expr1, op.strip(), expr2)
    elif op in set([
            "/", "divide", "div", "divided by",
            "%", "modulo", "mod",
            "//", "floor"]):
        op2, expr2 = evaluateStack(s)
        op1, expr1 = evaluateStack(s)
        # Handle division by zero gracefully
        if op2 == 0:
            return "undefined", "%s %s %s" % (expr1, op.strip(), expr2)
        else:
            val = opn[op](op1, op2)
            return val, "%s %s %s" % (expr1, op.strip(), expr2)
    elif op == "currency":
        curr_to, expr2 = evaluateStack(s)
        curr_to = curr_to.upper()
        curr_from, expr1 = evaluateStack(s)
        curr_from = curr_from.upper()
        curr_amount, expr0 = evaluateStack(s)
        val, expr, rate, rate_updated = convert_currency(
            curr_amount, curr_from, curr_to)
        # "%s %s %s %s" % (curr_amount, curr_from, op.strip(), curr_to)
        return round(val, 4), expr
    elif op == "PI":
        val = math.pi  # 3.1415926535
        return val, op
    elif op == "E":
        val = math.e  # 2.718281828
        return val, op
    elif op == "today":
        val = datetime.date.today()
        return val, op
    elif op == "yesterday":
        val = datetime.date.today() - datetime.timedelta(days=1)
        return val, op
    elif op == "tomorrow":
        val = datetime.date.today() + datetime.timedelta(days=1)
        return val, op
    elif op in fn:
        op1, expr1 = evaluateStack(s)
        val = fn[op](op1)
        return val, "%s(%s)" % (op, expr1)
    elif re.match(RE_TIMEDELTA, op, re.IGNORECASE):
        m = re.match(RE_TIMEDELTA, op, re.IGNORECASE)
        amount = long(m.group(1))
        what = m.group(2).lower()
        if what.startswith("day"):
            val = timedelta(days=amount)
        elif what.startswith("week"):
            val = timedelta(weeks=amount)
        elif what.startswith("month"):
            val = timedelta(months=amount)
        elif what.startswith("year", expr=expr):
            val = timedelta(years=amount)
        else:
            val = ""
        return val, op
    # elif op[0].isalpha():
    #    if re.match(RE_ROMAN_NUMERALS, op, re.IGNORECASE):
    #        if re.match(RE_VALID_ROMAN_NUMBER, op, re.IGNORECASE):
    #            i = roman_to_int(op)
    #            return i, op.upper()
    #        else:
    #            return 0L, "Not valid roman numeral"
    #    return 0L, 0L
    elif op.isalpha() and len(op) == 3:  # in RATES.exchange_rates.keys():
        return op, op
    elif op == "()":
        val, expr = evaluateStack(s)
        return val, "(%s)" % expr
    else:
        val = 0L
        try:
            val = long(op)
        except ValueError:
            try:
                val = float(op)
            except ValueError:
                raise
            except OverflowError:
                raise
        except OverflowError:
            raise
        return val, str(op).strip()


def evaluate(expression):
    BNF.expr_stack = []
    expression, formatted_expression = text2num(expression)

    expression = expression.replace(u"\u00D7", "*")  # X symbol
    expression = expression.replace(u"\u03c0", "PI")  # Greek PI symbol

    # print "CONVERTED:", expression, formatted_expression
    res = BNF.get_bnf().parseString(expression)
    # print "STACK:", BNF.expr_stack[:]
    # print "RES: ", res, "STACK: ", BNF.expr_stack
    val, expr = evaluateStack(BNF.expr_stack[:])
    #expr = " ".join(res)
    # print expr

    if isinstance(val, datetime.timedelta):
        val = "%d days %d hours %d minutes" % (
            val.days,  # IGNORE:E1103
            val.seconds // 3600, val.seconds % 3600 // 60
        )

    return val, expr


def test(s, expVal):
    BNF.expr_stack = []
    results = BNF.get_bnf().parseString(s)
    val = evaluateStack(BNF.expr_stack[:])
    # print val.__class__, expVal.__class__
    if val == expVal:
        # print s, "=", val, results, "=>", BNF.expr_stack
        return expVal
    else:
        return s + "!!!", val, "!=", expVal, results, "=>", BNF.expr_stack

if __name__ == "__main__":

    #    @timelimit(4)

    test("9", 9)
    test("-9", -9)
    test("--9", 9)
    test("-E", -math.e)
    test("9 + 3 + 6", 9 + 3 + 6)
    test("9 pLUs 3 aDD 6", 9 + 3 + 6)
    test("9 + 3 / 11", 9 + 3.0 / 11)
    test("(9 + 3)", (9 + 3))
    test("(9+3) / 11", (9 + 3.0) / 11)
    test("9 - 12 - 6", 9 - 12 - 6)
    test("9 minus 12 SUBTRACT 6", 9 - 12 - 6)
    test("9 - (12 - 6)", 9 - (12 - 6))
    test("2*3.14159", 2 * 3.14159)
    test("3.1415926535*3.1415926535 / 10", 3.1415926535 * 3.1415926535 / 10)
    test("PI * PI / 10", math.pi * math.pi / 10)
    test("pi times pi divide 10", math.pi * math.pi / 10)
    test("PI*PI/10", math.pi * math.pi / 10)
    test("PI^2", math.pi**2)
    test("pi power 2", math.pi**2)
    test("round(PI^2)", round(math.pi**2))
    test("6.02E23 * 8.048", 6.02E23 * 8.048)
    test("e / 3", math.e / 3)
    test("sin(PI/2)", math.sin(math.pi / 2))
    test("trunc(E)", int(math.e))
    test("trunc(-E)", int(-math.e))
    test("round(E)", round(math.e))
    test("round(-E)", round(-math.e))
    test("E^pi", math.e**math.pi)
    test("2^3^2", 2**3**2)
    test("2^3+2", 2**3 + 2)
    test("2^9", 2**9)
    test("2**3**2", 2**3**2)
    test("2**3+2", 2**3 + 2)
    test("2**9", 2**9)
    test("sgn(-2)", -1)
    test("sgn(0)", 0)
    test("sgn(0.1)", 1)

    test("9^9^2", float(9**9**2))

    test("1232 // 2.3", 1232 // 2.3)
    test("10.3 % 6", 10.3 % 6)

    test("10 xor 24", 10 ^ 24)
    test("6 or 1", 6 | 1)
    test("7 and 3", 7 & 3)

    test("sqrt(16)", 4)
    test("squared(4)", 4 * 4)
    test("cubed(4)", 4 * 4 * 4)
    test("one plus one", 1 + 1)
    test("thirty plus hundred", 30 + 100)

"""
Test output:
>pythonw -u fourFn.py
9 = 9.0 ['9'] => ['9']
9 + 3 + 6 = 18.0 ['9', '+', '3', '+', '6'] => ['9', '3', '+', '6', '+']
9 + 3 / 11 = 9.27272727273 ['9', '+', '3', '/', '11'] => ['9', '3', '11', '/', '+']
(9 + 3) = 12.0 [] => ['9', '3', '+']
(9+3) / 11 = 1.09090909091 ['/', '11'] => ['9', '3', '+', '11', '/']
9 - 12 - 6 = -9.0 ['9', '-', '12', '-', '6'] => ['9', '12', '-', '6', '-']
9 - (12 - 6) = 3.0 ['9', '-'] => ['9', '12', '6', '-', '-']
2*3.14159 = 6.28318 ['2', '*', '3.14159'] => ['2', '3.14159', '*']
3.1415926535*3.1415926535 / 10 = 0.986960440053 ['3.1415926535', '*', '3.1415926535', '/', '10'] => ['3.1415926535', '3.1415926535', '*', '10', '/']
PI * PI / 10 = 0.986960440109 ['PI', '*', 'PI', '/', '10'] => ['PI', 'PI', '*', '10', '/']
PI*PI/10 = 0.986960440109 ['PI', '*', 'PI', '/', '10'] => ['PI', 'PI', '*', '10', '/']
PI^2 = 9.86960440109 ['PI', '^', '2'] => ['PI', '2', '^']
6.02E23 * 8.048 = 4.844896e+024 ['6.02E23', '*', '8.048'] => ['6.02E23', '8.048', '*']
e / 3 = 0.90609394282 ['E', '/', '3'] => ['E', '3', '/']
sin(PI/2) = 1.0 ['sin', 'PI', '/', '2'] => ['PI', '2', '/', 'sin']
trunc(E) = 2 ['trunc', 'E'] => ['E', 'trunc']
E^PI = 23.1406926328 ['E', '^', 'PI'] => ['E', 'PI', '^']
2^3^2 = 512.0 ['2', '^', '3', '^', '2'] => ['2', '3', '2', '^', '^']
2^3+2 = 10.0 ['2', '^', '3', '+', '2'] => ['2', '3', '^', '2', '+']
2^9 = 512.0 ['2', '^', '9'] => ['2', '9', '^']
sgn(-2) = -1 ['sgn', '-2'] => ['-2', 'sgn']
sgn(0) = 0 ['sgn', '0'] => ['0', 'sgn']
sgn(0.1) = 1 ['sgn', '0.1'] => ['0.1', 'sgn']
>Exit code: 0
"""
