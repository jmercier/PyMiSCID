"""
This is the possible implementation of Bonjour. For now, we only have avahi
implementation so this is the default used
"""
#import logging
#logger = logging.getLogger(__name__)

#import twisted.internet


#try:
#    import twisted.internet.glib2reactor
#    if isinstance(twisted.internet.reactor, twisted.internet.glib2reactor.Glib2Reactor):
from avahi_browser import BonjourServiceDiscovery, BonjourServicePublisher, BonjourTypeDiscovery
#        if logger.isEnabledFor(logging.INFO):
#            logger.info("Bonjour : reactor matched with GLIB2 reactor, using default Avahi implementation")

#except Exception,err:
#    pass

#try:
#    import codebench.twisted.internet.qt4reactor
#    if isinstance(twisted.internet.reactor, codebench.twisted.internet.qt4reactor.QTReactor):
#        from kde4_browser import BonjourServiceDiscovery, BonjourServicePublisher, BonjourTypeDiscovery
#        if logger.isEnabledFor(logging.INFO):
#            logger.info("Bonjour : reactor matched with QT4 reactor, using the KDE4 implementation")
#except Exception, err:
#    pass

