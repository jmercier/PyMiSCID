# Copyright (c) 2009-2011 J-Pascal Mercier
#
#
#
import weakref

import bip.protocol as protocol
import reactor

from codebench import events

from cstes import UNBOUNDED_PEERID



class ConnectorBase(protocol.BIPFactory):
    """
    """
    __pid_generator__ = \
            protocol.peerid_generator_factory(protocol.PeerID(UNBOUNDED_PEERID).base())

    input = output = True

    def __init__(self, peerid = None):
        """
        :param peerid: The peerid of the given connector
        """
        peerid = self.__pid_generator__.next() if peerid is None else peerid
        protocol.BIPFactory.__init__(self, peerid)

    def __hash__(self):
        """
        """
        return __peerid__

    def send(self, msg, peerid = None):
        """
        This function send a message to a peer. If peerid is not provided,
        send the message to all peers.

        :param msg: The actual message
        :param peerid: The recipient peerid
        """
        if not self.output:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Trying to send msg through an Input Only Connector")
            raise RuntimeError("Sending msg through an Input Only Connector")

        if peerid is None:
            map(lambda proto: proto.send(msg, self.peerid), self.peers.itervalues())
        else:
            self.peers[peerid].send(msg, self.peerid)

    def close(self, peerid = None):
        """
        This function close a connection with a peer. If peerid is not provided,
        close all remaining connections.

        :param peerid: The peerid
        """
        if peerid is None:
            map(lambda proto: proto.stop(), self.peers.itervalues())
        else:
            self.peers[peerid].stop()

    def connect(self, addr, port, token = False):
        """
        """
        reactor.Reactor().connectTCP(addr, port, self)
        return True

    def received(self, proto, peerid, msgid, msg):
        protocol.BIPFactory.received(self, proto, peerid, msgid, msg)

        if msgid != 0 and not self.input:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Trying to send msg through an Input Only Connector")
            raise RuntimeError("Sending msg through an Input Only Connector")

    def TXTRecord(self, record = None):
        """
        This method describe the connector as a txt record (python dict) for dnssd.
        """
        if record is None:
            record = {}
        if self.running == 0:
            raise RuntimeError("Cannot get txt record of an stopped connector")
        record[self.name] = \
                        ''.join([self.txt_prefix, TXT_SEPARATOR, str(self.tcp)])
        return record

    def start(self, tcpport = 0, udpport = 0):
        stcp = reactor.Reactor().listenTCP(tcpport, self)
        addr, self.tcp = stcp.getsockname()

        self.udp = None

        #sudp = reactor.listenUDP(0, self)
        #addr, self.udp = sudp.getsockname()


class Connector(ConnectorBase, events.EventDispatcherBase):
    """
    Connector + Simple RAW Event dispatcher for object callback.
    """
    __pid_generator__ = \
            protocol.peerid_generator_factory(protocol.PeerID(UNBOUNDED_PEERID).base())

    events = ['connected', 'disconnected', 'received']

    def __init__(self, *args, **kw):
        ConnectorBase.__init__(self, *args, **kw)
        events.EventDispatcherBase.__init__(self)

    def connected(self, proto, rpeerid):
        """
        Callback override from BIP protocol when connection is made

        :param proto: The actual protocol object where the event occured
        """
        ConnectorBase.connected(self, proto, rpeerid)
        self.connectedEvent(rpeerid)

    def disconnected(self, proto, rpeerid):
        """
        Callback override from BIP protocol when connection is lost


        :param proto: The actual protocol object where the event occured
        """
        ConnectorBase.disconnected(self, proto, rpeerid)
        self.disconnectedEvent(rpeerid)

    def received(self, proto, peerid, msgid, msg):
        """
        Callback override from BIP protocol when message is received

        :param proto: The actual protocol object where the event occured
        :param msg: The string message

        """
        ConnectorBase.received(self, proto, peerid, msgid, msg)
        if len(msg) != 0:
            self.receivedEvent(msg)


