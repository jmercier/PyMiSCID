import connector
import rpc
import bonjour.avahi_browser as bonjour
import random

from codebench.decorators import singleton

class Service(object):
    name = "Unknown"

    def __init__(self):
        for attrname in dir(self.__class__):
            attr = getattr(self.__class__, attrname)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, connector.ConnectorBase):
                setattr(self, attrname, attr())

    def start(self):
        self.connectors = {}

        self.publisher = bonjour.BonjourServicePublisher()

        self.control = rpc.RPCConnector()


        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, connector.ConnectorBase):
                self.connectors[attrname] = attr
        for c in self.connectors:
            self.connectors[c].start()

        self.publisher.publish(self.name, self.control.tcp, "_bip._tcp")

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

    print ser.connectors['c'].tcp, ser2.connectors['c'].tcp

    import reactor
    reactor.Reactor().run()

    ser.stop()
    ser2.stop()

