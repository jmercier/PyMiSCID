#
"""
This module
"""
from protocol import BIPBaseProtocol
from twisted.internet.protocol import Factory

import logging
logger = logging.getLogger(__name__)

BIP_GREETING_TIMEOUT = 1  # in seconds

class BIPFactory(Factory):
    """
    This is an implementation of the Twisted factory for the BIP protocol 
    """
    protocol = BIPBaseProtocol
    timeout = BIP_GREETING_TIMEOUT
    service = None

    def startedConnecting(self, connector):
        """
        Callback from the protocol (Just Logging)
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Started Connecting ...")

    def clientConnectionLost(self, connector, reason):
        """
        Callback from the prorocol (Nothin')
        """
        pass

    def clientConnectionFailed(self, connector, reason):
        """
        Callback from the protocol (Just Logging)
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Connection Failed")

    def buildProtocol(self, addr):
        """
        Building protocol. Add the current service to the observer list for the
        protocol
        """
        proto = Factory.buildProtocol(self, addr)
        if self.service is not None:
            proto.addObserver(self.service)
        else:
            if logger.isEnabledFor(logging.CRITICAL):
                logger.critical("Proto built without any srv : won't do much")
        return proto


