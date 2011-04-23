from __future__ import print_function

import connector
import rpc
import bonjour.avahi_browser as bonjour
import random

from codebench.decorators import singleton


from standard import UNBOUNDED_PEERID, \
                     TXT_SEPARATOR, \
                     OUTPUT_CONNECTOR_PREFIX, \
                     INPUT_CONNECTOR_PREFIX, \
                     IO_CONNECTOR_PREFIX

connector.Connector.txt_description = IO_CONNECTOR_PREFIX
connector.IConnector.txt_description = INPUT_CONNECTOR_PREFIX
connector.OConnector.txt_description = OUTPUT_CONNECTOR_PREFIX

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

connector.Connector.__bases__ += (ConnectorMixin,)

class Service(object):
    def __init__(self):
        for attrname in dir(self.__class__):
            attr = getattr(self.__class__, attrname)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, connector.ConnectorBase):
                setattr(self, attrname, attr())

        self.consts = {"name" : "Unknown"}

    def start(self):
        record = {}
        self.connectors = {}

        self.publisher = bonjour.BonjourServicePublisher()

        self.control = rpc.RPCConnector()

        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, connector.ConnectorBase):
                self.connectors[attrname] = attr
        for c in self.connectors:
            self.connectors[c].name = c
            self.connectors[c].start()
            self.connectors[c].TXTRecord(record = record)
        print(record)

        self.publisher.publish(self.name, self.control.tcp, "_bip._tcp", txt = record)

    def stop(self):
        for c in self.connectors:
            self.connectors[c].close()
        self.publisher.unpublish()
        del self.publisher
        del self.connectors

if __name__ == '__main__':
    @singleton
    class S(Service):
        name = 'euh'
        c = connector.Connector

    @singleton
    class S1(Service):
        name = "EUH2"
        def __init__(self):
            self.c = connector.Connector()

    ser = S()
    ser2 = S1()

    ser.start()
    ser2.start()

    print(ser.connectors['c'].tcp, ser2.connectors['c'].tcp)

    import reactor
    reactor.Reactor().run()

    ser.stop()
    ser2.stop()

