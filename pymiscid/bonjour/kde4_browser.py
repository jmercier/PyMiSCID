import logging
import re
import socket

from PyKDE4.dnssd import DNSSD as dnssd
from PyQt4.QtCore import pyqtSignature, SIGNAL
from codebench import events

logger = logging.getLogger(__name__)

re_mdns = re.compile(r"(-[1-9])?\.local[\.]?$")

class BonjourTypeDiscovery(events.ThreadsafeEventDispatcher):
    """
    """
    events = ['added', 'removed']
    def __init__(self, filt = None):
            events.ThreadsafeEventDispatcher.__init__(self)
            self.filter = filt
            self.browser = dnssd.ServiceTypeBrowser()
            print self.browser.connect (self.browser, SIGNAL
                                        ("serviceTypeAdded(onst QString &)"),
                                  self.__domain_added__)
            print self.browser.connect (self.browser, SIGNAL
                                        ("serviceTypeRemoved(onst QString &)"),
                                  self.__domain_removed__)

    def run(self):
            self.browser.startBrowse()

    @pyqtSignature("dataUpdated(const QString &)")
    def __domain_added__(self, type):
        print type
        if (self.filter is None) or str(type).startswith(self.filter):
            if logger.isEnabledFor(logging.INFO):
                logger.info("%s domain discovered : %s" % (self.filter, type))
            self.addedEvent(type)

    @pyqtSignature("dataUpdated(const QString &)")
    def __domain_removed__(self, type):
        if (self.filter is None) or str(type).startswith(self.filter):
            if logger.isEnabledFor(logging.INFO):
                    logger.info("%s domain removed : %s" % (self.filter, type))
            self.removedEvent(type)


class BonjourServiceDiscovery(events.ThreadsafeEventDispatcher):
    events = ['added', 'removed']
    def __init__(self, ty):
        self.ty = ty
        events.EventDispatcherBase.__init__(self)
        self.discoverer = dnssd.ServiceBrowser(ty)
        self.discoverer.serviceAdded.connect(self.__service_added__)
        self.discoverer.serviceRemoved.connect(self.__service_removed__)

    def run(self):
        self.discoverer.startBrowse()

    def __service_added__(self, srv):
            srv.resolve()
            rname = srv.serviceName()
            rhost = re_mdns.split(str(srv.hostName()))[0]
            rport = srv.port()
            rtype = srv.type()
            family, socktype, proto, canonname, (raddr, unknown) = socket.getaddrinfo(rhost, None, socket.AF_INET,
                                                        socket.SOCK_RAW, socket.IPPROTO_IP, socket.AI_CANONNAME)[0]
            txt = srv.textData()
            kw = {}
            for k in txt:
                kw[str(k)] = str(txt[k])
            if logger.isEnabledFor(logging.DEBUG):
                fname = kw["name"].strip("/c") if "name" in kw else "UNKNOWN"
                logger.debug("%s relolved[%s] : %s on %s - %s (%s)" 
                        % (fname, self.ty, rname, raddr, rhost, rport))
            self.addedEvent(rname, re_mdns.split(rhost)[0], raddr, rport, kw, rhost)


    def __service_removed__(self, srv):
            rname = srv.serviceName()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Service removed[%s] : %s" % (self.ty, rname))
            self.removedEvent(rname)


class BonjourServicePublisher(object):
    publisher = None
    def __init__(self):
        self.publisher = dnssd.PublicService()

    def publish(self, name, port, domain, txt = None):
        self.unpublish()
        if txt is None:
            txt = {}
        self.publisher.setServiceName(name)
        self.publisher.setPort(port)
        self.publisher.setType(domain)
        self.publisher.setTextData(txt)
        self.publisher.publishAsync()

    def unpublish(self):
        if (self.publisher is not None) and self.publisher.isPublished():
            self.publisher.stop()
