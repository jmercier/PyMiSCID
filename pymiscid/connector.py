# Copyright (c) 2009-2011 J-Pascal Mercier
#
#
#
import weakref
import copy

import bip.protocol as protocol
import reactor

from codebench import events

import logging
logger = logging.getLogger(__name__)



class ConnectorBase(protocol.BIPFactory):
    """
    """
    input = output = True

    __tcp       = None
    description = "It's a trap"
    structure   = "raw"

    def __get_peerid(self):
        return self.__peerid

    def __set_peerid(self, peerid):
        if len(self.peers) != 0:
            raise AttributeError("Peer ID is read-only when active connection exists")

        self.__peerid = peerid

    def __init__(self, peerid = None):
        """
        :param peerid: The peerid of the given connector
        """
        self.peerid = protocol.PeerID() if peerid is None else peerid
        protocol.BIPFactory.__init__(self)

    def __hash__(self):
        """
        Basic hash of a connector
        """
        return self.peerid

    def send(self, msg, peerid = None, udp = False):
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
            map(lambda proto: proto.send(msg, self.peerid, udp = udp), self.peers.values())
        else:
            self.peers[peerid].send(msg, self.peerid, udp = udp)

    def connect(self, cdesc):
        """
        """
        if isinstance(cdesc, tuple):
            addr, port = cdesc
        else:
            addr, port = cdesc.addr, cdesc.tcp


        reactor.Reactor().connectTCP(addr, port, self)


    def received(self, proto, peerid, msgid, msg):
        protocol.BIPFactory.received(self, proto, peerid, msgid, msg)
        if  (not self.input) and (msgid != 0):
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Receiving message through an Output Only Connection")
            raise RuntimeError("Receiving msg through an Output Only Connector")


    def start(self, tcpport = 0, udpport = 0, peerid = None):
        self.peerid         = self.peerid if peerid is None else peerid
        stcp                = reactor.Reactor().listenTCP(tcpport, self)
        addr, self.__tcp    = stcp.getsockname()


        #sudp = reactor.listenUDP(0, self)
        #addr, self.udp = sudp.getsockname()


    def __get_tcp_port(self):
        if self.__tcp is None:
            self.start()
        return self.__tcp
    tcp = property(__get_tcp_port)




class Connector(ConnectorBase, events.EventDispatcherBase):
    """
    Connector + Simple RAW Event dispatcher for object callback.
    """
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
        if msgid != 0:
            self.receivedEvent(msg)


class IConnector(Connector):
    input = False

class OConnector(Connector):
    output = False



