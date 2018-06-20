# -*- coding: utf-8 -*-
# vim:set tabstop=4 softtabstop=4 shiftwidth=4 expandtab:
#
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

# TODO: Do not change the source expression when replacing (don't change spacing and don't remove parenteses)
# TODO: When the computation is the same as last time and "put" is possible, don't add it again
# TODO: Give user a hint about home-currency
# TODO: Give user a hint about no echange-rate for some currency

import logging  # @UnusedImport
import re
import itertools

from xml.sax.saxutils import escape as xml_escape

from enso import selection
from enso.contrib.calc import fourfn
from enso.contrib.calc.exchangerates import converter

from enso.commands import CommandManager, CommandObject
from enso.commands.factories import ArbitraryPostfixFactory
from enso.contrib.scriptotron.tracebacks import safetyNetted
from enso.contrib.scriptotron.ensoapi import EnsoApi
from enso.contrib.recentresults import RecentResult

from text2num import text2num, format_number_local

ensoapi = EnsoApi()


def _replace_special_unicode_chars(expr):
    expr = expr.replace(u"\N{MINUS SIGN}", "-")
    expr = expr.replace(u"\N{EM DASH}", "-")
    expr = expr.replace(u"\N{EN DASH}", "-")
    expr = expr.replace(u"\N{HYPHEN}", "-")
    expr = expr.replace(u"\N{HYPHEN-MINUS}", "-")
    expr = expr.replace(u"\N{SMALL HYPHEN-MINUS}", "-")
    expr = expr.replace(u"\N{FULLWIDTH HYPHEN-MINUS}", "-")

    expr = expr.replace(u"\N{PLUS SIGN}", "+")
    expr = expr.replace(u"\N{SMALL PLUS SIGN}", "+")
    expr = expr.replace(u"\N{FULLWIDTH PLUS SIGN}", "+")

    expr = expr.replace(u"\N{MULTIPLICATION SIGN}", "*")
    expr = expr.replace(u"\N{MULTIPLICATION X}", "*")
    expr = expr.replace(u"\N{HEAVY MULTIPLICATION X}", "*")

    expr = expr.replace(u"\N{DIVISION SIGN}", "/")
    expr = expr.replace(u"\N{DIVISION SLASH}", "/")

    expr = expr.replace(u"\N{SUPERSCRIPT TWO}", " squared")

    expr = expr.replace(u"\N{FULLWIDTH EQUALS SIGN}", "=")
    expr = expr.replace(u"\N{SMALL EQUALS SIGN}", "=")
    expr = expr.replace(u"\N{MODIFIER LETTER SHORT EQUALS SIGN}", "=")

    expr = expr.replace(u"\N{MATHEMATICAL LEFT ANGLE BRACKET}", "(")
    expr = expr.replace(u"\N{MATHEMATICAL RIGHT ANGLE BRACKET}", ")")

    expr = expr.replace(u"\N{MATHEMATICAL SANS-SERIF BOLD ITALIC SMALL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL SANS-SERIF BOLD CAPITAL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL BOLD ITALIC SMALL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL BOLD ITALIC CAPITAL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL ITALIC SMALL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL ITALIC CAPITAL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL BOLD SMALL PI}", " pi ")
    expr = expr.replace(u"\N{MATHEMATICAL BOLD CAPITAL PI}", " pi ")
    expr = expr.replace(u"\N{SCRIPT SMALL E}", "e")

    expr = expr.replace(u"\N{FULLWIDTH POUND SIGN}", "GBP")
    expr = expr.replace(u"\N{POUND SIGN}", "GBP")
    expr = expr.replace(u"\N{EURO-CURRENCY SIGN}", "EUR")
    expr = expr.replace(u"\N{EURO SIGN}", "EUR")
    expr = expr.replace(u"\N{DOLLAR SIGN}", "USD")
    expr = expr.replace(u"\N{SMALL DOLLAR SIGN}", "USD")
    expr = expr.replace(u"\N{FULLWIDTH DOLLAR SIGN}", "USD")
    expr = expr.replace(u"\N{FULLWIDTH YEN SIGN}", "JPY")
    expr = expr.replace(u"\N{YEN SIGN}", "JPY")

    # Convert all occurrences of multiple contiguous whitespace
    # characters to a single space character.
    expr = re.sub(r"\s+", " ", expr)

    return expr


def _convert_language(expression):
    #expression = expression.replace(' mod ', ' % ')
    #expression = expression.replace(' plus ', ' + ')
    #expression = expression.replace(' add ', ' + ')
    #expression = expression.replace(' minus ', ' - ')
    #expression = expression.replace(' subtract ', ' - ')
    #expression = expression.replace(' times ', ' * ')
    #expression = expression.replace(' mul ', ' * ')
    #expression = expression.replace(' multiply ', ' * ')
    #expression = expression.replace(' div ', ' / ')
    #expression = expression.replace(' divide ', ' / ')
    #expression = expression.replace(' floor ', ' // ')
    #expression = expression.replace(' modulo ', ' % ')
    #expression = expression.replace(' power ', ' ** ')

    #expression = expression.replace(' xor ', ' ^ ')
    #expression = expression.replace(' and ', ' & ')
    #expression = expression.replace(' or ', ' | ')
    #expression = expression.replace(' not ', ' ~ ')

    curr_repl = (
        (u"\N{FULLWIDTH POUND SIGN}", "GBP"),
        (u"\N{POUND SIGN}", "GBP"),
        (u"\N{EURO-CURRENCY SIGN}", "EUR"),
        (u"\N{EURO SIGN}", "EUR"),
        (u"\N{DOLLAR SIGN}", "USD"),
        (u"\N{SMALL DOLLAR SIGN}", "USD"),
        (u"\N{FULLWIDTH DOLLAR SIGN}", "USD"),
        (u"\N{FULLWIDTH YEN SIGN}", "JPY"),
        (u"\N{YEN SIGN}", "JPY"),
    )

    for symbol, iso in curr_repl:
        expression = re.sub(
            ur"%s(\.?[0-9]+(\.([0-9]+)?)?)" % re.escape(symbol),
            ur"\1 %s" % iso,
            expression)

    return expression


def _fast_calc(expression=None):
    if not expression:
        return None, None

    if isinstance(expression, str):
        expression = expression.decode("utf-8", "ignore")
    expression = _convert_language(expression)

    # print expression = expression.replace(' in ', ' % ')

    if expression.endswith("="):
        expression = expression[:-1]

    try:
        result, expr = fourfn.evaluate(expression)
        return result, unicode(expr)
    except ZeroDivisionError, e:
        logging.warning(e)
        return e[0], expression
    except ArithmeticError, e:
        logging.warning(e)
        return e[1], expression
    except Exception, e:
        logging.warning(e)
        return str(e), expression


def cmd_calculate(ensoapi, expression=None):
    """ Calculate %s
    <p>Calculate mathematical expression.</p>
    """

    got_selection = False
    if expression is None:
        seldict = ensoapi.get_selection()
        if seldict.get(u"text"):
            selected_text = seldict[u'text'].strip().strip("\0")
        else:
            selected_text = None
        if selected_text:
            expression = selected_text
            got_selection = expression is not None

    if expression is None:
        ensoapi.display_message("No expression. Please type or select some mathematic expression.")
        return

    if isinstance(expression, str):
        expression = expression.decode("utf-8", "ignore")
    expression = _convert_language(expression)

    if "=" in expression:
        expression = expression.split("=")[0].strip()
        append_result = True
    else:
        append_result = False
    """
    123
    4354
    3*3
    234+23
    asd
    fdf
    123

    """
    if expression.count("\n"):
        new_lines = []
        total = 0
        for line in expression.split("\n"):
            leading_whitespace = "".join(s for s in itertools.takewhile(str.isspace, line))
            try:
                result, expr = fourfn.evaluate(line.strip())
                new_lines.append(u"%s%s" % (leading_whitespace, unicode(result)))
                total += long(result)
            except ZeroDivisionError, e:
                logging.warning(e)
                new_lines.append(line.rstrip())
            except ArithmeticError, e:
                logging.warning(e)
                new_lines.append(line.rstrip())
            except Exception, e:
                logging.warning(e)
                new_lines.append(line.rstrip())
        expression = " +\n".join(new_lines) + "\n"
        result = total
        append_result = True
    else:
        try:
            result, expression = fourfn.evaluate(expression)
        except ZeroDivisionError, e:
            logging.warning(e)
            return str(e), expression
        except ArithmeticError, e:
            logging.warning(e)
            return e[1], expression
        except Exception, e:
            logging.warning(e)
            return str(e), expression

    pasted = False
    if got_selection:
        if append_result:
            pasted = selection.set({"text": expression.strip() + " = " + unicode(result)})
        else:
            pasted = selection.set({"text": unicode(result)})

    _ = pasted  # keep pylint happy

    msg = u"%s = %s" % (xml_escape(expression), xml_escape(unicode(result)))
    RecentResult.get().push_result(result, msg)

    """
    #TODO: Testing for return value of selection.set() is not working,
    # returns always True, even after the pasting didn't succeed.
    if pasted:
        msg = u"%s = %s" % (xml_escape(expression), xml_escape(unicode(result)))
        RecentResult.get().push_result(result, msg)
        #displayMessage(
        #    u"<p>%s</p><p>Use <command>put</command> command to insert result.</p><caption>%s</caption>"
        #    % (xml_escape(unicode(result)), xml_escape(expression)))
        #paste_command = get_paste_command()
        #if paste_command:
        #    paste_command.update_pastings({".calculation result" : unicode(result)})
    """
    return result, unicode(expression)


class CalculateCommand(CommandObject):
    u""" 
    \u201ccalculate {expression}\u201d command

    Calculate mathematical expression. 
    """

    HELP_TEXT = "expression"
    PREFIX = "calculate "
    NAME = "%s{%s}" % (PREFIX, HELP_TEXT)

    DESCRIPTION_NO_PREVIEW = u"Calculate {expression}"
    DESCRIPTION_PREVIEW = u"Calculate %s = %s"
    DESCRIPTION_ERROR = u"Calculate %s = ?"

    OVERRIDE_ALLOWED_KEYCODES = {
        191: "/",  # Instead of ? (helps access / without shift on laptop keyboards)
        # replace [ with (
        34: "(",
        # replace ] with )
        35: ")",
        # replace = with +
        21: "+",
    }

    def __init__(self, expression=None):
        super(CalculateCommand, self).__init__()

        if expression:
            expression = _replace_special_unicode_chars(expression)

        self.expression = expression
        if expression:
            result, expr = _fast_calc(expression)
            if result is not None:
                expr = expr.replace(" * ", u" \u00D7 ")  # X symbol
                expr = expr.replace("pi", u"\u03c0").replace("PI", u"\u03c0")  # Greek pi symbol
                self.setDescription(
                    self.DESCRIPTION_PREVIEW
                    % (expr, format_number_local(result)))
            else:
                self.setDescription(self.DESCRIPTION_ERROR % expression)
        else:
            self.setDescription(self.DESCRIPTION_NO_PREVIEW)

    @safetyNetted
    def run(self):
        result, expression = cmd_calculate(ensoapi, self.expression)
        if hasattr(self, "updateResultsHistory"):
            self.updateResultsHistory(expression)


class SetHomeCurrencyCommand(CommandObject):

    def __init__(self, code=None):
        super(SetHomeCurrencyCommand, self).__init__()

        if code:
            code = code.upper()
        self.code = code

    @safetyNetted
    def run(self):
        if self.code is None:
            curr = converter.get_home_currency()
            ensoapi.display_message(
                u"%s: %s" % (curr, converter.get_currency_rates().exchange_rates[curr]["name"]),
                u"Your current home currency")
        elif not converter.is_supported_currency(self.code):
            ensoapi.display_message(
                u"\"%s\" is not a valid ISO-currency-code!" % self.code)
        else:
            converter.set_home_currency(self.code)
            ensoapi.display_message(
                u"%s: %s" % (self.code, converter.get_currency_rates().exchange_rates[self.code]["name"]),
                u"Home currency have been set to")


class CalculateCommandFactory(ArbitraryPostfixFactory):
    """
    Generates a "learn as open {name}" command.
    """

    HELP_TEXT = CalculateCommand.HELP_TEXT
    PREFIX = CalculateCommand.PREFIX
    NAME = CalculateCommand.NAME

    last_postfix = None
    last_cmd_obj = None

    results_history = []

    def updateResultsHistory(self, expression=None):
        if expression and expression not in CalculateCommandFactory.results_history:
            CalculateCommandFactory.results_history.append(expression)
        self.setParameterSuggestions(CalculateCommandFactory.results_history)

    def _generateCommandObj(self, postfix):
        if postfix is None:
            cmd = CalculateCommand(postfix)
            cmd.updateResultsHistory = self.updateResultsHistory
            cmd.getParameterSuggestions = self.getParameterSuggestions
            self.updateResultsHistory()
            # cmd.setName(self.NAME)
            return cmd
        else:
            if CalculateCommandFactory.last_postfix == postfix:
                return CalculateCommandFactory.last_cmd_obj
            else:
                cmd = CalculateCommand(postfix)
                cmd.updateResultsHistory = self.updateResultsHistory
                cmd.getParameterSuggestions = self.getParameterSuggestions
                # cmd.setName(self.NAME)
                CalculateCommandFactory.last_postfix = postfix
                CalculateCommandFactory.last_cmd_obj = cmd
                self.updateResultsHistory()
                return cmd


class SetHomeCurrencyCommandFactory(ArbitraryPostfixFactory):
    """
    Generates a "set home currency {code}" command.
    """

    PREFIX = "set home currency "
    HELP_TEXT = "iso code"
    NAME = "%s{%s}" % (PREFIX, HELP_TEXT)
    DESCRIPTION = "Set your home currency"

    def _generateCommandObj(self, postfix):
        cmd = SetHomeCurrencyCommand(postfix)
        cmd.setDescription(self.DESCRIPTION)
        return cmd


# ----------------------------------------------------------------------------
# Plugin initialization
# ---------------------------------------------------------------------------

def load():
    # Register commands
    try:
        CommandManager.get().registerCommand(
            CalculateCommandFactory.NAME,
            CalculateCommandFactory()
        )
        CommandManager.get().registerCommand(
            SetHomeCurrencyCommandFactory.NAME,
            SetHomeCurrencyCommandFactory()
        )
    except Exception, e:
        logging.error(e)

# ----------------------------------------------------------------------------
# Doctests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import doctest
    doctest.testmod()
