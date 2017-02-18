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
#   enso.messages
#
# ----------------------------------------------------------------------------

"""
    The Message component of the Enso user interface.

    In the context of the UI, a Message is simply some
    information that needs to be presented to the user, but which is
    not specifically requested by the user as content.  For example,
    the ever familiar "king kong is not a command" informs the user
    that the commmand name they typed is not valid.

    In the spirit of Archy, Primary Messages are messages that are
    presented to the user in a transparent overlay in a somewhat
    intrusive way.  Primary Messages disappear as soon as the user makes
    any action, such as moving the mouse or pressing a key.

    Besides these Primary Messages, Enso borrows the concept of
    non-invasive messages from such applications as Firefox and Google
    Talk.  These are called "Mini Messages".  These Mini Messages
    appear in the lower right-hand corner of the user's screen, and
    may persist for some length of time.  This is to provide the user
    with information about something that continues to be true.  For
    example, a Message might be "Launching Macromedia Fireworks",
    which tells the user tha a requested action is being worked on,
    and that message might persist until there is some other visible
    manifestation of the fact that Fireworks is being opened, such as
    a splash screen or intro window appearing.

    But the essential concept behind the design of this component is
    that a Message object simply encapsulates some piece of
    information the user may care about.  A Message may be a Primary
    Message, a Mini Message, both, or neither.  We may introduce
    additional means of providing the user access to messages in the
    long run, such as a Message Graveyard.

    A Message object starts in client code, where it is told:
      (a) what information the user should be presented with (possibly
          in different forms for different purposes),
      (b) what kind of message it is (Primary, Mini, etc.)
    Then the Message is added to the singleton Message managar, which
    is responsible for seeing that the message is displayed in all the
    appropriate ways.


    ** Message Life Cycle **

    A message begins as a chunk of text that Enso wishes to present to
    the user.  Client code creates a new Message object containing an
    XML representation of this text.  Client code also tells the
    Message object whether or not it is primary and mini, and if it is
    mini, under what conditions it should be removed.

    The Message object is given to the Message manager, which
    immediately checks whether the message should be displayed as a
    primary message.  If so, then the message is displayed as the
    primary message immediately, replacing the current primary message
    if there is one.

    If the Message object is not supposed to be displayed as a primary
    message, the message manager immediately checks to see whether it
    should be displayed as a mini message.  If so, it adds it to the
    queue of mini messages that should be displayed.  However, if it
    should be displayed as mini message, then there is some condition
    under which it should no longer be displayed as a mini message.
    If that condition is true, then the message is not added to the
    mini message queue.  At this point, the message is finished, and
    disappears.

    If the Message object is displayed as a primary message, then when
    the primary message is dismissed (key press, mouse move, etc.),
    then the Message manager checks to see whether it should also be
    displayed as a mini message.  Again, if it should be displayed as
    a mini message and the condition for its removal is not yet met,
    the message is added to the mini message queue.  Otherwise, the
    message is finished.

    Once a Message object is added to the mini message queue, it is
    displayed along with any other existing mini messages.
    Periodically, the mini message queue checks to see whether each
    mini message is finished; if so, then it removes the message from
    the display, and the message is finished.

    The moral of this story is: think of "mini" and "primary" as
    behaviors that belong to a single message, not different types of
    messages.
"""

# ----------------------------------------------------------------------------
# Imports
# ----------------------------------------------------------------------------

import time
import logging


# ----------------------------------------------------------------------------
# Message Object
# ----------------------------------------------------------------------------

class Message:
    """
    The Message interface for generating user information messages.

    This class is intended to be sub-classed by client code into
    classes that have specific behaviors.  To understand what the
    various behaviors of a message mean, check the life-cycle
    description in the module documentation.

    For example, a simple message might be created like this:

      >>> class MyPrimaryMessage( Message ):
      ...     def __init__( self, text ):
      ...         Message.__init__( self,
      ...                           isPrimary = True,
      ...                           isMini = True,
      ...                           fullXml = text )
      ...         self.finished = False
      ...     def isFinished( self ):
      ...         return self.finished
      >>> myMsg = MyPrimaryMessage( "<p>Hello there!</p>" )

    Then the message manager and display classes can query
    the message object for information:

      >>> myMsg.isPrimary()
      True
      >>> myMsg.isMini()
      True
      >>> myMsg.getPrimaryXml()
      '<p>Hello there!</p>'
      >>> myMsg.getFullXml()
      '<p>Hello there!</p>'

    And we can tell the message manager when the message is done being
    a mini message, by making isMessageFinised() return True:

      >>> myMsg.isFinished()
      False
      >>> myMsg.finished = True
      >>> myMsg.isFinished()
      True
    """

    def __init__( self,
                  fullXml,
                  primaryXml = None,
                  miniXml = None,
                  isPrimary = False,
                  isMini = False,
                  waitTime = None ):
        """
        Initializes the message object. Subclasses should be careful
        to call this if they override the constructor.

        isPrimary is a boolean determining whether or not the message
        should be displayed as a primary message.

        isMini is a boolean determining whether or not the message
        should be displayed as a mini message.

        fullXml is the main XML representaion of the message.

        primaryXml is an XML representation specific to the message's
        appearance as a primary message; this is optional.

        miniXml is an XML representation specific to the message's
        appearance as a mini message; this is optional.
        """

        self.__isPrimary = isPrimary
        self.__isMini = isMini

        self.__fullXml = fullXml
        self.__primaryXml = primaryXml
        self.__miniXml = miniXml
        self.__waitTime = waitTime


    def isPrimary( self ):
        """
        If true, this Message should be displayed as a primary
        message.  Otherwise, this Message should not be a primary
        message.
        """

        return self.__isPrimary

    def isMini( self ):
        """
        If true, this Message should be displayed as a mini message.
        Otherwise, this Message should not be a mini message.
        """

        return self.__isMini

    def getFullXml( self ):
        """
        Retrieves the full XML of the entire contents of this
        message.
        """

        return self.__fullXml

    def getPrimaryXml( self ):
        """
        Gets an XML representation appropriate for displaying
        as a primary message.
        """

        if self.__primaryXml != None:
            return self.__primaryXml
        else:
            return self.getFullXml()

    def getMiniXml( self ):
        """
        Gets an XML representation appropriate for displaying
        as a mini message.
        """

        if self.__miniXml != None:
            return self.__miniXml
        else:
            return self.getFullXml()

    def isFinished( self ):
        """
        Abstract method: Implemented by sub-classes to indicate that
        the message is finished, i.e., no longer needs to persist in
        the mini message queue.

        MUST be implemented by any mini message subclass.
        """

        if self.isMini():
            raise NotImplementedError()
        else:
            raise AssertionError( "isFinished() called on non-mini message." )

    def getWaitTime(self):
        return self.__waitTime



class ConditionMiniMessage(Message):
    """
    Message class that checks function determining whether the message is ready
    to disappear.

    """

    def __init__( self,
                  primaryXml = None,
                  miniXml = None,
                  is_finished_func = None):
        Message.__init__(self,
            fullXml = None,
            primaryXml = primaryXml,
            miniXml = miniXml,
            isPrimary = (primaryXml is not None),
            isMini = True)

        assert is_finished_func and callable(is_finished_func),\
            "is_finished_func parameter muste be callable and must return "\
            "True if mini-message is finished and should disappear."
        self.__is_finished_func = is_finished_func
        self.__manager = MessageManager.get()

    def isFinished( self ):
        if not self.__manager.isPrimaryMessageFinished(self):
            return False

        try:
            if self.__is_finished_func():
                return True
        except Exception as e:  #IGNORE:W0703
            logging.error(e)
            return False


class TimedMiniMessage(Message):
    """
    Message class that adds minimal timing to the mini-messages.

    Additional argument to_wait specifies minimum time in seconds
    during which the mini-message should stay on screen.

    Default value is None, where window stay on screen until cleared
    by user (using 'hide mini messages' command).
    """

    def __init__( self,
                  primaryXml = None,
                  miniXml = None,
                  waitTime = None):
        Message.__init__(self,
            fullXml = None,
            primaryXml = primaryXml,
            miniXml = miniXml,
            isPrimary = (primaryXml is not None),
            isMini = True)

        self.__wait = waitTime
        self.__started = None
        self.__manager = MessageManager.get()

    def isFinished( self ):
        if self.__started is None:
            if self.__manager.isPrimaryMessageFinished(self):
                self.__started = time.time()
            else:
                return False

        if self.__wait is None:
            return False
        elif time.time() - self.__started < self.__wait:
            return False
        else:
            return True


# ----------------------------------------------------------------------------
# MESSAGE MANAGER
# ----------------------------------------------------------------------------

class MessageManager:
    """
    Singleton class for managing the various forms of messages Enso uses.
    """

    __instance = None

    @classmethod
    def get( cls ):
        if not cls.__instance:
            from enso.messages.primarywindow import PrimaryMsgWind
            from enso.messages.miniwindows import MiniMessageQueue
            from enso.events import EventManager

            cls.__instance = cls( EventManager.get(),
                                  PrimaryMsgWind,
                                  MiniMessageQueue )
        return cls.__instance

    def __init__( self, eventManager, primaryMsgWindClass,
                  miniMsgWindClass ):
        """
        Instantiates the message manager and any windows used to
        display messages.
        """

        self.__evtManager = eventManager

        # The class that will be used to display primary messages.
        self.__primaryMsgWindClass = primaryMsgWindClass

        # The class that will be used to display mini messages.
        self.__miniMsgWindClass = miniMsgWindClass

        # The singleton primary message object. This saves
        # a reference to the Message that is being displayed
        # as the primary message for as long as it is displayed.
        self.__primaryMessage = None

        # Indicates that primary-message has finished display and has
        # disappeared. This is used in mini-message classes to detect
        # the exact start of mini-message display.
        self._isPrimaryMessageFinished = True

        # The window that will display primary messages.
        self.__primaryMsgWind = None
        # The window that will display mini messages.
        self.__miniMessageWind = self.__miniMsgWindClass(
            self,
            self.__evtManager
            )

        self.__messageGraveyard = []
        self.__onDismissalFunc = None


    def newMessage( self, msg, onDismissal=None, position=(None,None) ):
        """
        Adds a new message to the queue, which will get displayed and
        saved in all appropriate ways.
        """

        self.__addToGraveyard( msg )

        if msg.isPrimary():
            self.__newPrimaryMessage( msg )
            if onDismissal and not callable(onDismissal):
                raise Exception("onDismissal parameter must be callable")
            self.__onDismissalFunc = onDismissal
        elif msg.isMini() and not msg.isFinished():
            self.__newMiniMessage( msg )


    def onDismissal( self ):
        """
        Called by the primary message window when the primary message
        has been dismissed.  Note that the PM may still be on the
        screen when this function is called (e.g., it may be doing its
        fade-out animation).
        """

        #logging.info( "Primary message dismissed." )
        if self.__primaryMessage is None:
            return

        oldMsg = self.__primaryMessage
        if oldMsg.isMini() and not oldMsg.isFinished():
            self.__newMiniMessage( oldMsg )
        self.__primaryMessage = None

        if self.__onDismissalFunc:
            # Run onDismissal function if CTRL key is used to dismiss the message
            try:
                # TODO: Implement this on all platforms, currently it works only on Win32
                # Quite impossible to do in Linux (there is no API to access keyboard physical state)
                import win32con  # @UnresolvedImport
                import win32api  # @UnresolvedImport

                # If CTRL key is being held
                if win32api.GetAsyncKeyState(win32con.VK_CONTROL) << 1:  # @UndefinedVariable
                    # Wait for CTRL key release before executing the dismissal function
                    while win32api.GetAsyncKeyState(win32con.VK_CONTROL) << 1:  # @UndefinedVariable
                        time.sleep(0.01)
                    try:
                        self.__onDismissalFunc()
                    except Exception as e:
                        logging.error(e)
            except:
                pass
            finally:
                self.__onDismissalFunc = None


    def onMiniMessageFinished( self ):
        """
        Called by the mini message window when a mini-message has
        completely finished doing anything it needs to do, including
        on-screen animations and the like.
        """

        pass

    def onPrimaryMessageFinished( self ):
        """
        Called by the primary message window when it's completely
        finished doing anything it needs to do, including on-screen
        animations and the like.
        """
        self._isPrimaryMessageFinished = True
        del self.__primaryMsgWind
        self.__primaryMsgWind = None


    def getRecentMessage( self ):
        return self.__messageGraveyard[0] if len(self.__messageGraveyard) > 0 else None


    def displayRecentMessage( self ):
        msg = self.getRecentMessage()
        if msg:
            if msg.isPrimary():
                self.__newPrimaryMessage( msg )
            elif msg.isMini() and not msg.isFinished():
                self.__newMiniMessage( msg )
            return True
        else:
            return False


    def __addToGraveyard( self, msg ):
        """
        Adds the msg to the message graveyard, where the user
        can access it for ever and ever.

        NOTE: This currently does nothing, as the message
        graveyard has not been implemented.
        """

        # LONGTERM TODO: Add the full xml representation of the
        # message to the message graveyard.
        self.__messageGraveyard.insert(0, msg)
        if len(self.__messageGraveyard) > 50:
            del self.__messageGraveyard[-1]


    def __newMiniMessage( self, msg ):
        """
        Adds msg to the list of currently displayed mini messages.
        """

        self.__miniMessageWind.addMessage( msg )


    def __newPrimaryMessage( self, msg, on_dismissal=None ):
        """
        Causes msg to be displayed as the current primary message.
        """

        if not self.__primaryMsgWind:
            self.__primaryMsgWind = self.__primaryMsgWindClass(
                self,
                self.__evtManager
                )

        oldMsg = self.__primaryMessage
        if oldMsg is not None:
            if oldMsg.isMini() and not oldMsg.isFinished():
                self.__newMiniMessage( oldMsg )

        self.__primaryMessage = msg
        if on_dismissal is not None:
            self.__primaryMsgWind.setOnDismissalAction(on_dismissal)
        self.__primaryMsgWind.setMessage( msg )


    def isPrimaryMessageFinished(self, msg):
        return self.__primaryMessage != msg


    def finishMessages( self ):
        """
        Causes all mini messages to vanish immediately.
        """

        self.__miniMessageWind.hideAll()


    def finishPrimaryMessage( self, skip_animation = False ):
        if self.__primaryMessage.isPrimary():
            self.__primaryMsgWind.dismiss(skip_animation)


# ----------------------------------------------------------------------------
# Convenience functions
# ----------------------------------------------------------------------------

def displayMessage( msgXml, primaryMsg=True, miniMsg=False, miniMsgXml=None,
    primaryWaitTime=None, miniWaitTime=None, onDismissal=None ):
    """
    Displays a simple primary message with optional mini message.

    Optionally wait time argument specifies minimum time in seconds
    during which the mini-message should stay on screen and can't be dismissed
    by mouse or keyboard activity.
    
    Optional onDismissal function can be specified. It will be executed when
    CTRL key is used to dismiss the message.
    """

    if miniMsg or miniMsgXml is not None:
        if miniMsgXml is None:
            miniMsgXml = msgXml
        msg = TimedMiniMessage(
            primaryXml = (msgXml if primaryMsg else None),
            miniXml = miniMsgXml,
            waitTime = miniWaitTime
            )
    else:
        msg = Message(
            isPrimary = True,
            isMini = False,
            fullXml = msgXml,
            waitTime = primaryWaitTime
            )

    MessageManager.get().newMessage( msg, onDismissal )


def displayRecentMessage():
    """
    Displays recent primary/mini message. Returns False if there was no message.
    """
    return MessageManager.get().displayRecentMessage()


def hideMessage(skip_animation = False):
    return MessageManager.get().finishPrimaryMessage(skip_animation)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

# vim:set tabstop=4 shiftwidth=4 expandtab
