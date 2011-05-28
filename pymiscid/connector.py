# Copyright (c) 2009-2011 J-Pascal Mercier
#
#
#
import weakref

import bip.protocol as protocol
import reactor

from codebench import events

from standard import UNBOUNDED_PEERID


class ConnectorBase(protocol.BIPFactory):
    """
    """

    input = output = True

    __tcp__ = None

    def __init__(self):
        """
        :param peerid: The peerid of the given connector
        """
        protocol.BIPFactory.__init__(self)

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

        self.__tcp__ = None

    def connect(self, *args):
        """
        """
        if len(args) == 1:
            # PROXY
            pass

        if len(args) == 2:
            addr, port = args

        reactor.Reactor().connectTCP(addr, port, self)
        return True

    def received(self, proto, peerid, msgid, msg):
        protocol.BIPFactory.received(self, proto, peerid, msgid, msg)

        if msgid != 0 and not self.input:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Trying to send msg through an Input Only Connector")
            raise RuntimeError("Sending msg through an Input Only Connector")

    def start(self, tcpport = 0, udpport = 0, peerid = None):
        self.peerid = protocol.PeerID() if peerid is None else peerid
        stcp = reactor.Reactor().listenTCP(tcpport, self)
        addr, self.__tcp__ = stcp.getsockname()

        self.udp = None

        #sudp = reactor.listenUDP(0, self)
        #addr, self.udp = sudp.getsockname()


    def __get_tcp_port__(self):
        if self.__tcp__ is None:
            self.start()
        return self.__tcp__

    tcp = property(__get_tcp_port__)



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
        if len(msg) != 0:
            self.receivedEvent(msg)


class IConnector(Connector):
    output = False

class OConnector(Connector):
    output = False



