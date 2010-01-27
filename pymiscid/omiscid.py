#
"""
This is the standard OMiSCID api module. It install the twisted reactor
(if not already installed) and defines the function to run the reactor.
"""
# Installing the main glibreactor for twisted
try:
    from twisted.internet import glib2reactor
    glib2reactor.install()
except ImportError, err:
    pass
except AssertionError, err:
    pass

from twisted.internet import reactor

import thread

# Import some interesting omiscid type
from connector import INPUT, OUTPUT, INOUTPUT
from variable import CONSTANT, READ_WRITE, READ
from filters import *

# Importing and Creating the default ServiceFactory
from factory import ServiceFactory
factory = ServiceFactory()

def run(inthread = False):
    """
    This method starts the OMiSCID main loop.
    """
    if inthread:
         thread.start_new_thread(reactor.run, (), {"installSignalHandlers" : False})
    else:
        reactor.run(installSignalHandlers = True)

def stop():
    """
    This method stop the OMiSCID main loop.
    """
    reactor.stop()

