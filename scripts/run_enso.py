#! /usr/bin/env python

import os
import logging

import enso

if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO )

    ensorc_path = os.path.expanduser(os.path.join("~", ".ensorc"))
    if os.path.isfile(ensorc_path):
        logging.info( "Loading '%s'." % ensorc_path )
        contents = open( ensorc_path, "r" ).read()
        compiledContents = compile( contents + "\n", ensorc_path, "exec" )
        exec compiledContents in {}, {}
    else:
        logging.warning(".ensorc file can't be read!")

    enso.run()

# vim:set tabstop=4 shiftwidth=4 expandtab:
