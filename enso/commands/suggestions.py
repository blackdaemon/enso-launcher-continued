# Copyright (c) 2008, Humanized, Inc.
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
# THIS SOFTWARE IS PROVIDED BY Humanized, Inc. ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL Humanized, Inc. BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# ----------------------------------------------------------------------------
#
#   enso.commands.suggestions
#
# ----------------------------------------------------------------------------

"""
    Classes for encapsulating suggestions (including auto-completions).
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import re
import enso.utils.strings
import enso.utils.xml_tools

# This is used in loop so better to import the function directly to avoid lookup penalty
from enso.utils.xml_tools import escape_xml

# ----------------------------------------------------------------------------
# Suggestion Objects
# ----------------------------------------------------------------------------

class Suggestion:
    """
    An object the encapsulates a "suggestion".  A "suggestion" is
    essentially a string from a list that is similar to some source
    string.

    Suggestion objects keep track of the original source string, and
    has utility methods for marking-up the suggestion to indicate
    similarities to the source string (i.e., which characters of the
    suggestion are the same as the original, which are added, and
    which are altered).
    """

    def __init__( self, originalText, suggestedText, helpText = None, prefix_end=None, start=None, end=None, suggestedPrefix=None ):
        """
        Initializes the Suggestion: suggestedText is the suggestion
        for originalText.
        """

        assert isinstance( originalText, basestring )
        assert isinstance( suggestedText, basestring )

        # The "source" or "original" text is the text that the user
        # typed.
        self.__source = originalText
        # The "suggestion" is the text that very nearly matches
        # the user's typed text.
        self.__suggestion = suggestedText
        self.__suggestedPrefix = suggestedPrefix

        # The "help" text is text that is not actually part of the
        # suggestion, per-se, but should be displayed after the
        # suggestion to indicate that something should follow the
        # suggestion before it is complete and valid.
        self.__helpText = helpText

        # The xml representation of this suggestion; will not be
        # created until requested.
        self.__xml = None

        # The completion of the user text to the next word.
        #self.__completion = None

        self.__prefix_end = prefix_end
        self.__start = start
        self.__end = end

        # For performance reasons, compute the "nearness" value
        # and cache it.
        self._nearness = self.__getNearness()

    def getHelpText( self ):
        return self.__helpText

    """
    TODO:This is broken because the __transform() function has been optimized
    and is not setting __completion variable.
    It is not used anywhere in the code anyway...

    def toNextWord( self ):
        ""
        Returns the simple string representation of the suggestion, i.e.,
        the exact suggested text.

        Example:

          >>> s = Suggestion( 'fo', 'foo bar' )
          >>> s.toNextWord()
          'foo '
        ""

        if self.__completion is None:
            self.__transform()

        return self.__completion
    """

    def toText( self ):
        """
        Returns the simple string representation of the suggestion, i.e.,
        the exact suggested text.

        Example:

          >>> s = Suggestion( 'fo', 'foo' )
          >>> s.toText()
          'foo'
        """

        return self.__suggestion

    def getSource( self ):
        """
        Returns the "source" string, i.e., the string for which this
        object is a suggestion.

        Example:

          >>> s = Suggestion( 'fo', 'foo' )
          >>> s.getSource()
          'fo'
        """

        return self.__source

    def getSuggestedPrefix( self ):
        """
        """

        return self.__suggestedPrefix

    def __getNearness( self ):
        """
        Returns a number between 0 and 1 indicating how near the
        original string this suggestion is; 0 means totally different,
        and 1 means exactly the same.

        NOTE: As long as the return value remains as described,
        this method may be overridden to implement custom notions of
        "nearness".
        """
        result = enso.utils.strings.stringRatio( self.__source,
                                                 self.__suggestion )
        assert (result >= 0) and (result <= 1),\
            "string-ratio is not between 0 and 1: %0.1f" % result
        return result

    def __eq__( self, other ):
        """
        Considers two suggestions to be equal if they suggest the same
        string.
        """

        if not isinstance( other, Suggestion ):
            # The other object isn't a Suggestion, so they can't
            # possibly be equal.
            return False
        else:
            return self.toText() == other.toText()

    def __ne__( self, other ):
        """
        Considers two suggestions to be unequal if they do not suggest the
        same text.
        """

        # Simply return the inverse of __eq__
        return not self.__eq__( other )

    def __cmp__( self, other ):
        """
        Compares two suggestions on the basis of nearness.
        """

        # NOTE: This function is called SO OFTEN, that using getter's
        # for the nearness values incurs a NOTICEABLE performance
        # penalty.

        # Returning the inverse of the value, because 1 is near and 0
        # is far.

        # Original:
        #return - cmp( self._nearness, other._nearness )

        if self._nearness < other._nearness: #IGNORE:W0212
            return 1
        elif self._nearness > other._nearness: #IGNORE:W0212
            return -1
        else:
            # If the nearness is equal, return alphabetical order
            return cmp(self.__suggestion, other.__suggestion) #IGNORE:W0212
    
    def __str__( self ):
        return self.toText()
        
    def toXml( self ):
        """
        Transforms the suggestion into a simple XML string.  There are
        three tags:
          <ins></ins> marks an "insertion", i.e., something added to
            the original text to make the suggestion.
          <alt></alt> marks an "alteration", i.e., a substring of the
            original string was replaced with a new substring to make
            the suggestion.
          <help></help> marks a "help" text, i.e., a string that
            indicates the suggestion should be followed by some
            additional text; this string is for the user's aid, and is
            not part of the suggestion proper.
        Anything not contained in these tags was part of the original
        text.

        NOTE: The return value does not have a "root" tag, and is
        therefore not well-formed XML.

        Here is a simple example using insertions and help text:

          >>> Suggestion( 'fo', 'foo', 'fooObject' ).toXml()
          'fo<ins>o</ins><help>fooObject</help>'

        Here is a simple example using alterations:

          >>> Suggestion( 'fog', 'foo' ).toXml()
          'fo<alt>o</alt>'

        The default implementation finds the the largest substring of
        the original text that (a) includes the first character of the
        original text and (b) is entirely contained in the suggestion.
        It then repeats this with the remainder of the original text.

        So, for instance, if our original text is 'foobar' and our
        suggestion text is 'foo the bar', the default implementation
        will first match 'foo' to part of the suggestion; at this
        point the remainder of the original text will be 'bar', which
        it will find a substring for in the suggestion text as well.
        This is shown in the following example:

          >>> Suggestion( 'foobar', 'foo the bar' ).toXml()
          'foo<ins> the </ins>bar'

        Furthermore, if there is no initial substring of the original
        text in the suggestion text (i.e., condition 'a' from above) ,
        the first character is removed from the original text and the
        algorithm proceeds as described above, marking a corresponding
        part of the suggestion string as an alteration, if
        applicable:

          >>> Suggestion( 'zzzfo', 'gfoo' ).toXml()
          '<alt>g</alt>fo<ins>o</ins>'

          >>> Suggestion( 'zzzfo', 'foo' ).toXml()
          'fo<ins>o</ins>'

        Finally, if no substring of the original text matches the
        suggestion text, the entire suggestion text is returned as an
        alteration:

          >>> Suggestion( 'zzz', 'defghi' ).toXml()
          '<alt>defghi</alt>'

        NOTE: This method is intended to be overriden by subclasses
        that have specialized ways of determining what was original
        and what was inserted or altered.
        """

        # This class is read-only; the only "setters" are through the
        # constructor.  If we have previously computed the xml value,
        # return that cached value.
        if self.__xml == None:
            self.__transform()

        return self.__xml


    def __transform( self ):
        if self.__start is not None:
            #s = escape_xml(self.__suggestion)
            xmlText = "%s<ins>%s</ins>%s<ins>%s</ins>" % (
                escape_xml(self.__suggestion[:self.__prefix_end]),
                escape_xml(self.__suggestion[self.__prefix_end:self.__prefix_end+self.__start]),
                escape_xml(self.__suggestion[self.__prefix_end+self.__start:self.__prefix_end+self.__end]),
                escape_xml(self.__suggestion[self.__prefix_end+self.__end:])
            )
            if self.__suggestedPrefix and xmlText.startswith(self.__suggestedPrefix):
                xmlText = "<prefix>%s</prefix>%s" % (escape_xml(self.__suggestedPrefix), xmlText[len(self.__suggestedPrefix):])
            # Finally, add help text, if it exists.
            if self.__helpText is not None:
                xmlText = "%s<help>%s</help>" % (xmlText, escape_xml(self.__helpText))
            self.__xml = xmlText
            return
        else:
            pass


        # We are going to "use up" both the source string and the
        # suggestion
        unusedSource = self.__source[:]
        unusedSuggestion = self.__suggestion[:]

        # The xml representation
        xmlText = ""

        # The "to the next word" completion.
        completion = ""


        # If we cannot match an initial substring of unusedSource,
        # then we are going to peel off characters one-by-one into
        # this variable.  These characters have been lost in the
        # suggestion, and will cause "insertions" to instead be
        # "alterations".
        unmatchedChars = ""

        # BEGIN SOURCE-STRING LOOP

        # Each iteration of this loop should reduce the length of
        # unusedSource, and this loop ends when unusedSource is empty.
        while len(unusedSource) > 0:
            # Save a copy of unusedSource, so we know if it changes.
            oldUnusedSource = unusedSource[:]

            # Loop from the full length of unusedSource down to one
            # character
            for i in range( len(unusedSource), 0, -1 ):
                # The initial substring we are trying to locate.
                target = unusedSource[:i]

                # BEGIN TARGET-FOUND CONDITION
                if target in unusedSuggestion:
                    # Search normally from begining
                    index = unusedSuggestion.find( target )
                    # Search on word boundaries. This is different from \b in
                    # that it considers also the underscore character as a word boundary.
                    m = re.match(r".*[^0-9a-zA-Z](%s)" % re.escape(target), unusedSuggestion, re.I)
                    if m and m.groups() and m.start(1) > index:
                        # Prefer word boundary match
                        index = m.start(1)
                        # index, m.start(1)
                    if index > 0:
                        if len(unmatchedChars) > 0:
                            # There were unused characters in the
                            # source, and there were characters in the
                            # unused suggestion before the target, so
                            # the next "inserted" portion of the
                            # suggestion becomes an "alteration"
                            # instead.
                            xmlFormat = "<alt>%s</alt>"
                        else:
                            xmlFormat = "<ins>%s</ins>"
                        xmlText += xmlFormat % escape_xml(
                            unusedSuggestion[:index]
                            )
                        # NOTE: Do not add inserted characters to the
                        # 'next word' completion.
                    # Whether or not there were characters between
                    # the start of the unused suggestion and "here",
                    # any unmatched chars are now defunct.
                    unmatchedChars = ""
                    xmlText += escape_xml( target )
                    completion += target
                    unusedSuggestion = unusedSuggestion[index+len(target):]
                    unusedSource = unusedSource[i:]
                    # The target was found and unusedSource was
                    # modified; we exit the for-loop (to be entered
                    # again if unusedSource is still nonempty).
                    break
                # END TARGET-FOUND CONDITION

            # Either unusedSource is smaller, or it is the same as
            # oldUnusedSource.  If it is the same as old unusedSource,
            # then there was no match of a beginning substring, so we
            # remove the first character and store it as an "unused
            # character", which will become part of an "altered
            # substring", if there is a match to a later substring.
            if unusedSource == oldUnusedSource:
                unmatchedChars += unusedSource[0]
                unusedSource = unusedSource[1:]

            assert len( unusedSource ) < len( oldUnusedSource ), \
                   "Potential infinite loop condition; failed to reduce"\
                   " the length of the unused portion of the source string"\
                   " in toXml()"
        # END SOURCE-STRING LOOP

        # The source-string loop above only guarantees to use up the
        # source string; there may be an unused portion of the
        # suggestion left.  We append it to the xml string as an
        # insertion (or alteration, if appropriate).
        if len( unusedSuggestion ) > 0:
            if len( unmatchedChars ) > 0:
                format = "<alt>%s</alt>"
            else:
                format = "<ins>%s</ins>"
            unusedXml = escape_xml( unusedSuggestion )
            xmlText += format % unusedXml

            completion += unusedSuggestion.split(" ")[0]
            if " " in unusedSuggestion:
                completion += " "

        # Finally, add the help text, if it exists.
        if self.__helpText != None:
            xmlText += "<help>%s</help>" % self.__helpText

        if self.__suggestedPrefix and xmlText.startswith(self.__suggestedPrefix):
            xmlText = "<prefix>%s</prefix>%s" % (escape_xml(self.__suggestedPrefix), xmlText[len(self.__suggestedPrefix):])

        self.__xml = xmlText
        #print "COMPLETION: \"%s\"" % completion
        #self.__completion = completion


class AutoCompletion( Suggestion ):
    """
    Encapsulates a single auto-completed suggestion.

    Basically the same as a suggestion, except that it requires either
    (1) that each word of the original text be contained in the
    suggestion, or (2) that the suggestion be empty (indicating a
    failed autocompletion).
    """

    def __init__( self, originalText, suggestedText, helpText=None, prefix_end=None, start=None, end=None ):
        """
        Initializes the AutoCompletion.
        """

        # Enforce the object's preconditions.
        if len( suggestedText ) > 0:
            assertionText = "Attempted to create AutoCompletion %s from %s, "\
                            "but %s was not found."

            words = originalText.split( " " )
            # LONGTERM TODO: Don't handle this as a special case.
            if words[-1].endswith( "?" ):
                words[-1] = words[-1][:-1]
                words.append( "?" )
            for word in words:
                assert word in suggestedText, \
                       assertionText % ( suggestedText, originalText, word)

        # The text matches one of the class's two required conditions,
        # so initialize self as a Suggestion.

        Suggestion.__init__( self, originalText, suggestedText, helpText, prefix_end, start, end )

    def hasCompletion(self):
        return bool(self.toText())
