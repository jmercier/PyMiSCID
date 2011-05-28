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
                     IO_CONNECTOR_PREFIX, \
                     DESCRIPTION_VARIABLE_NAME, \
                     FULL_DESCRIPTION_VALUE, \
                     PART_DESCRIPTION_VALUE

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
    """
    """
    publisher = None
    name = "UnNamed"

    def __init__(self):
        for attrname in dir(self.__class__):
            attr = getattr(self.__class__, attrname)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, connector.ConnectorBase):
                setattr(self, attrname, attr())

        self.consts = {"name" : self.name}


    def start(self):
        """
        """
        if self.publisher is not None:
            return False

        # We never fully describe our service through txt record
        record = { DESCRIPTION_VARIABLE_NAME : PART_DESCRIPTION_VALUE }

        self.connectors = {}
        self.publisher = bonjour.BonjourServicePublisher()



        # Populating Connector Attribute
        for attrname in dir(self):
            attr = getattr(self, attrname)
            if isinstance(attr, connector.ConnectorBase):
                self.connectors[attrname] = attr


        peerid_gen = connector.protocol.PeerIDIterator()

        self.control = rpc.RPCConnector()
        self.control.name = self.name
        self.control.peerid = peerid_gen.next()

        for cname, peerid in zip(self.connectors, peerid_gen):
            c = self.connectors[cname]
            c.name = cname
            c.peerid = peerid
            c.start()
            c.TXTRecord(record = record)

        print(record)

        self.publisher.publish(self.name, self.control.tcp, "_bip._tcp", txt = record)

        return True


    def stop(self):
        """
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


if __name__ == '__main__':
    class S(Service):
        name = 'euh'
        c = connector.Connector

    class S1(Service):
        name = "EUH2"
        def __init__(self):
            Service.__init__(self)
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

