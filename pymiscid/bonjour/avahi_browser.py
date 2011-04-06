#!/usr/bin/env python2
#
# (c) copyright 2010-2011 - Jean-Pascal Mercier <jp.mercier@gmail.com>
# All rights reserved
#
#

"""
This method implement the Avahi Service Discovery for OMiSCID
"""

import logging
import re
import socket

import dbus
import avahi

try:
    from ..codebench import events
except Exception, err:
    print err
    from codebench import events

from dbus.mainloop.glib import DBusGMainLoop

logger = logging.getLogger(__name__)

re_mdns = re.compile(r"(-[1-9])?\.local[\.]?$")

class BonjourObject(object):
    """
    This is a basic bonjour object. It create the link through dbus to
    communicate with the avahi daemon.
    """
    __loop__ = None
    @classmethod
    def __initMainLoop__(cls):
            cls.__loop__ = DBusGMainLoop()

    def __init__(self, shared_loop = True):
        if not shared_loop:
                self.__loop__ = DBusGMainLoop()
        elif self.__loop__ is None:
                self.__initMainLoop__()
        self.__sbus__ = dbus.SystemBus(mainloop = self.__loop__)
        self.__siface__ = dbus.Interface(
                            self.__sbus__.get_object( avahi.DBUS_NAME,
                                                      avahi.DBUS_PATH_SERVER),
                            avahi.DBUS_INTERFACE_SERVER)

class BonjourTypeDiscovery(BonjourObject, events.MutexedEventDispatcher):
    """
    This class represent the avahi type discovery. This is intended to browse
    asynchronously the environment type. Can also be given a filter for a
    particular kind of subtype domain.
    """
    events = ['added', 'removed']
    def __init__(self, filt = None):
        """
        Can take a filter
        """
        BonjourObject.__init__(self)
        events.EventDispatcherBase.__init__(self)
        self.filter = filt

    def start(self):
        """
        Starts the discovery process.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Starting OMiSCID Domain Discovery ...")
        dom = 'local'
        dbrowser = self.__sbus__.get_object(avahi.DBUS_NAME, \
                            self.__siface__.ServiceTypeBrowserNew(avahi.IF_UNSPEC,\
                            avahi.PROTO_INET, dom, dbus.UInt32(0)))

        self.__sbiface__ = dbus.Interface(dbrowser, avahi.DBUS_INTERFACE_SERVICE_TYPE_BROWSER)
        self.__sbiface__.connect_to_signal("ItemNew", self.__domain_added__)
        self.__sbiface__.connect_to_signal("ItemRemove", self.__domain_removed__)

    def __domain_added__(self, a1, a2, dtype, domain, a5):
            if (self.filter is None) or dtype.startswith(self.filter):
                if logger.isEnabledFor(logging.INFO):
                        logger.info("%s domain discovered : %s" % (self.filter, dtype))
                self.addedEvent(str(dtype))

    def __domain_removed__(self, a1, a2, dtype, domain, a5):
            if (self.filter is None) or dtype.startswith(self.filter):
                if logger.isEnabledFor(logging.INFO):
                        logger.info("%s domain removed : %s" % (self.filter, dtype))
                self.removedEvent(str(dtype))

class BonjourServiceDiscovery(BonjourObject, events.MutexedEventDispatcher):
    """
    This object represent the main service discovery. It is meant to browse the
    know services and call the added, and removed method of the proxy_factory.
    """
    events = ['added', 'removed']

    def __init__(self, domain):
        """
        Domain type for the browsing
        """
        BonjourObject.__init__(self)
        events.EventDispatcherBase.__init__(self)
        self.domain = domain

    def start(self):
        """
        This method must be call to start the MDNS Service Discovery
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Starting Service Discovery at : %s" % (self.domain))
        dom = 'local' 
        flg = dbus.UInt32(0)

        sbrowser = self.__sbus__.get_object(avahi.DBUS_NAME, \
                            self.__siface__.ServiceBrowserNew(avahi.IF_UNSPEC,\
                            avahi.PROTO_INET, self.domain, dom, flg))

        self.__sbiface__ =  dbus.Interface(sbrowser, \
                            avahi.DBUS_INTERFACE_SERVICE_BROWSER)

        def service_added(interface, protocol, name, typ, domain, flags):
            """
            I don't need to comment this is nonsense
            """
            self.__siface__.ResolveService(interface, protocol,
                            name, typ, domain, avahi.PROTO_UNSPEC,
                            dbus.UInt32(0),
                            reply_handler = self.__resolve_handler__,
                            error_handler=self.__resolve_error__)

        self.__sbiface__.connect_to_signal("ItemNew", service_added)
        self.__sbiface__.connect_to_signal("ItemRemove", 
                                           self.__service_removed__)

    def __resolve_error__(self, msg):
        if logger.isEnabledFor(logging.WARNING):
            logger.warning("Avahi : %s " % (msg))


    def __resolve_handler__(self, riface, rproto, rname, rtype, rdomain, rhost,
                        raproto, raddr, rport, rtxt, rflags):
        string_txt = avahi.txt_array_to_string_array(rtxt)
        kw = {}
        rhost_prefix = re_mdns.split(rhost)[0]
        for i in string_txt:
            key, value = i.split('=',1)
            kw[key] = value

        try:
            family, socktype, proto, canonname, (dns_raddr, unknown) = \
                    socket.getaddrinfo( rhost_prefix, None, socket.AF_INET,
                                        socket.SOCK_RAW, socket.IPPROTO_IP,
                                        socket.AI_CANONNAME)[0]
            rhost = rhost_prefix
            raddr = dns_raddr
        except socket.gaierror:
            if logger.isEnabledFor(logging.INFO):
                logger.info("Cannot Resolve <%s> with dns using mdns instead ..."
                            % rhost_prefix)



        if logger.isEnabledFor(logging.DEBUG):
            fname = kw["name"].strip("/c") if "name" in kw else "UNKNOWN"
            logger.debug("%s relolved[%s] : %s on %s - %s (%s)" 
                        % (fname, self.domain, rname, raddr, rhost, rport))

        self.addedEvent(rname, rhost, raddr, rport, kw, rhost)

    def __service_removed__(self, rinterface, rprotocol, rname, rtype,
                            rdomain, rflags):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Service removed[%s] : %s" % (self.domain, rname))
        self.removedEvent(rname)

class BonjourServicePublisher(BonjourObject):
    """
    This object represent the publisher for DNSSD Service.
    """
    group = None

    def publish(self, name, port, domain, txt = None):
        """
        This method publish the service to the avahi daemon and keep the group
        object for further use.
        """
        self.unpublish()
        if txt is None:
            txt = {}
        if logger.isEnabledFor(logging.INFO):
            logger.info("Starting service on %d with description %s" % \
                                                                (port, str(txt)))
        bus = dbus.SystemBus()
        grp = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   self.__siface__.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        grp.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0),
                     name, domain, "", "",
                     dbus.UInt16(port), avahi.dict_to_txt_array(txt))

        grp.Commit()
        self.group = grp

    def unpublish(self):
        """
        Unpublish the current service.
        """
        if self.group is not None:
            self.group.Reset()
            self.group = None

    def __del__(self):
        self.unpublish()

if __name__ == '__main__':
    import gobject

    typedisc = BonjourTypeDiscovery("_bip")
    typedisc.start()

    def added(domain):
        print "Added : ", domain
    typedisc.addedEvent.addObserver(added)

    def removed(domain):
        print "Removed : ", domain
    typedisc.removedEvent.addObserver(removed)

    m = gobject.MainLoop()
    m.run()
