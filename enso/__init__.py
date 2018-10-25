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
#   enso
#
# ----------------------------------------------------------------------------

import enso.config

def run():
    """
    Initializes and runs Enso.
    """
    import logging
    import sys
    from enso.events import EventManager
    from enso.quasimode import Quasimode
    from enso import events, plugins, config, messages, quasimode, webui

    def except_hook(type, value, tback):
        # manage unhandled exception here
        logging.error(value)
        tback.print_exc()
        sys.__excepthook__(type, value, tback)  # then call the default handler

    sys.excepthook = except_hook

    eventManager = EventManager.get()
    Quasimode.install(eventManager)
    plugins.install(eventManager)

    webui_server = webui.start(eventManager)

    if enso.config.SHOW_SPLASH and config.OPENING_MSG_XML:
        eventManager.registerResponder(
            lambda: messages.displayMessage(config.OPENING_MSG_XML), 
            "init")

    try:
        eventManager.run()
    except SystemError as e:
        logging.error(e)
        import traceback
        traceback.print_exc()
        webui_server.stop()
    except SystemExit as e:
        logging.error(e)
        import traceback
        traceback.print_exc()
        webui_server.stop()
    except KeyboardInterrupt:
        webui_server.stop()
    except Exception as e:
        logging.error(e)
        import traceback
        traceback.print_exc()
        webui_server.stop()
    except:
        import traceback
        traceback.print_exc()
        webui_server.stop()
