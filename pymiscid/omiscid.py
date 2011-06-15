#
# @Author : Jean-Pascal Mercier <jean-pascal.mercier@agsis.com>
#
# @Copyright (C) 2010 Jean-Pascal Mercier
#
# All rights reserved.
#

from __future__ import print_function

import logging
logger = logging.getLogger(__name__)

import connector
import rpc
import bonjour.avahi_browser as bonjour
import random
import pwd
import os
import threading
import description
import bip.protocol as protocol
import codebench.events as events
import socket

from codebench.decorators import singleton


from standard import UNBOUNDED_PEERID, \
                     TXT_SEPARATOR, \
                     OUTPUT_CONNECTOR_PREFIX, \
                     INPUT_CONNECTOR_PREFIX, \
                     IO_CONNECTOR_PREFIX, \
                     DESCRIPTION_VARIABLE_NAME, \
                     FULL_DESCRIPTION_VALUE, \
                     PART_DESCRIPTION_VALUE, \
                     OMISCID_DOMAIN, \
                     CONSTANT_PREFIX

connector.Connector.txt_description     = IO_CONNECTOR_PREFIX
connector.IConnector.txt_description    = INPUT_CONNECTOR_PREFIX
connector.OConnector.txt_description    = OUTPUT_CONNECTOR_PREFIX

class ConnectorMixin(object):
    name = "UnNamed"
    def TXTRecord(self, record = None):
        """
        This method describe the connector as a txt record (python dict) for dnssd.
        """
        if record is None:
            record = {}
        record[self.name] = \
                        ''.join([self.txt_description, TXT_SEPARATOR, str(self.tcp)])

        return record

    def StructuredDescription(self):
        return dict(name = self.name,
                    peerid = int(self.peerid),
                    description = self.description,
                    attributes = [],
                    structure = self.structure,
                    tcp = self.tcp)


connector.Connector.__bases__ += (ConnectorMixin,)

class Service(object):
    """
    """
    publisher   = None
    name        = "UnNamed"
    description = "Hello Ground!!"

    def __init__(self):
        for attrname in dir(self.__class__):
            attr = getattr(self.__class__, attrname)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, connector.ConnectorBase):
                setattr(self, attrname, attr())

        self.consts = {"name" : self.name}



    def __init_control(self):
        """
        """
        peerid_gen  = connector.protocol.PeerIDIterator()

        self.control            = rpc.RPCConnector()
        self.control.name       = self.name
        self.control.peerid     = peerid_gen.next()

        self.control.bind(self)

        return peerid_gen


    def start(self, subdomain = None):
        """
        This function starts the service object. It publish it's description to
        DNS-SD and start the socket server of every underlying connectors.
        """
        if self.publisher is not None:
            return False

        # We never fully describe our service through txt record
        record = { DESCRIPTION_VARIABLE_NAME : PART_DESCRIPTION_VALUE ,
                   "name" : "%s/%s" % (CONSTANT_PREFIX, self.name),
                   "description" : "%s/%s" % (CONSTANT_PREFIX, self.description)}

        self.connectors     = {}
        self.publisher      = bonjour.BonjourServicePublisher()

        # Populating Connector Attribute from introspection
        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, connector.ConnectorBase):
                self.connectors[attrname] = attr

        peerid_gen  = self.__init_control()

        for cname, peerid in zip(self.connectors, peerid_gen):
            c           = self.connectors[cname]
            c.name      = cname
            c.peerid    = peerid

            c.start()
            c.TXTRecord(record = record)

        # Publishing our service through DNS-SD
        domain = OMISCID_DOMAIN if subdomain is None else "_bip_%s._tcp" % subdomain
        self.publisher.publish(str(self.control.peerid), self.control.tcp, domain, txt = record)

        return True


    def stop(self):
        """
        This method is stop the publisher and close every socket server in this
        service. All the underlying connection are closed.
        """
        if self.publisher is None:
            return False;

        for c in self.connectors:
            self.connectors[c].close()
        self.publisher.unpublish()

        self.publisher = None
        del self.connectors

        return True

    def __del__(self):
        self.stop()

    @rpc.remote_callable
    def get_description(self):
        c = [c.StructuredDescription() for c in self.connectors.itervalues()]
        return dict(connectors = c,
                    description = self.description,
                    name = self.name,
                    control = self.control.StructuredDescription(),
                    user = pwd.getpwuid(os.getuid())[0],
                    host = socket.gethostname())

    @rpc.remote_callable
    def get_peers(self):
        return [int(k) for k in self.control.peers.keys()]


class ServiceRepository(events.EventDispatcherBase):
    events = ['added', 'removed']

    def __init__(self, subdomain = ""):
        events.EventDispatcherBase.__init__(self)
        self.connector      = rpc.RPCConnector()
        self.descriptions   = {}
        self.deferreds      = {}
        self.bsd            = bonjour.BonjourServiceDiscovery(subdomain)
        self.lock           = threading.Lock()

        self.bsd.addObserver(self)
        self.connector.addObserver(self)
        self.bsd.start()

    def addObserver(self, observer, *args):
        events.EventDispatcherBase.addObserver(self, observer, *args)
        with self.lock:
            for p in self.descriptions:
                observer(p, *args)


    def added(self, peerid, host, addr, port, desc):
        self.connector.connect((addr, port))

    def removed(self, peerid):
        pid = protocol.PeerID(peerid)
        if pid in self.descriptions:
            with self.lock:
                p = self.descriptions.pop(pid)
            if logger.isEnabledFor(logging.INFO):
                logger.info("OMiSCID Service Removed [%s] %s" %
                            (str(peerid), p.name) )

            self.removedEvent(p)

    def connected(self, peerid):
        with self.lock:
            callback = rpc.MethodCallback(self.__serviceResolved, peerid)

            deferred = self.connector.call("get_description", callback = callback, peerid = peerid)
            self.deferreds[peerid] = deferred

    def __serviceResolved(self, answer, peerid):
        with self.lock:
            addr, port = self.connector.getPeerInfo(peerid)

            # For debian and such
            if addr == '127.0.0.1':
                addr = socket.gethostbyname(socket.gethostname())

            answer.update(dict(addr = addr, port = port, peerid = peerid))
            self.deferreds.pop(peerid)
            p = description.ServiceDescription(answer)
            self.descriptions[peerid] = p

        if logger.isEnabledFor(logging.INFO):
            addr, port = self.connector.getPeerInfo(peerid)
            logger.info("[%s] Resolved on [%s, %s] : [%s]" \
                        % (p.name, p.host, str(peerid), ", ".join([c.name for c in p.connectors])) )

        self.connector.close(peerid = peerid)

        self.addedEvent(p)

    def disconnected(self, peerid):
        if peerid in self.deferreds:
            with self.lock:
                del self.deferreds[peerid]


    def __del__(self):
        self.stop_event = True



if __name__ == '__main__':
    import codebench.log

    import logging.config
    logging.getLogger().setLevel(logging.DEBUG)

    services = []
    for i in range(1):
        class S(Service):
            name = 'Yeah_%d' % i
        for j in range(1):
            setattr(S, "c_%d" % j, connector.Connector)

        services.append(S())

    [s.start() for s in services]


    import reactor
    reactor.Reactor().run()

    [s.stop() for s in services]


