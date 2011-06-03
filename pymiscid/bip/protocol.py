#
"""
This is the implementation of the BIP protocol based on twisted.
"""

import random
import logging
import threading
import socket
import math
import reactor


logger = logging.getLogger(__name__)

LINE_ENDING = "\r\n"
BIP_HEADER_TEMPLATE = "%s %s %.8x %.8x" + LINE_ENDING
BIP_GREETING_TIMEOUT = 1  # in seconds

def PeerIDIterator(base = None):
    peerid = PeerID() if base is None else base
    for i in xrange(0xFF):
        yield peerid
        peerid += 1


class PeerID(int):
    """
    This class represent a peerid. Internally it is just a long int which with
    the method str always givin the hexadecimal value at the right length that
    is defined in the BIP Protocol.
    """
    __slots__ = []
    def __new__(cls, val = None):
        if val is None:
            val = random.randint(0, 0xFFFFFFFF) & 0xFFFFFF00
        elif isinstance(val, str):
            val = long(val, 16)
        return int.__new__(cls, val)

    def __str__(self):
        return ("%08.x" % self).upper()

    def __add__(self, val):
        return PeerID(val + self)

    def __sub__(self, val):
        return PeerID(val - self)

    def base(self):
        """
        This method returns the peerid of the service for the given peerid
        """
        return PeerID(self & 0xFFFFFFFF00)

    def __getid__(self):
        return self
    id = property(__getid__)



class PeerError(Exception):
    """
    A simple exception with the peerid.
    """
    def __init__(self, peerid, msg = ""):
        Exception.__init__(self, msg)
        self.peerid = peerid


def recv_into_wait(sock, buf, size):
    """
    This function block until all the bytes are received in the given buffer
    or the a socket timeout occured.
    """
    msglen = 0
    while msglen != size:
        recv_size = sock.recv_into(memoryview(buf)[msglen:], size - msglen)
        if recv_size == 0:
            raise RuntimeError("Connection Lost")

        msglen += recv_size
    return msglen


class BIPProtocol(threading.Thread):
    """
    """
    __name__            = 'BIP'
    __version__         = '1.0'
    __greeting_msg__    = "%s/%s" % (__name__, __version__)
    __hdr_size__        = len(BIP_HEADER_TEMPLATE %
                                (__greeting_msg__, str(PeerID(0)), 0, 0)) \
                                + len(LINE_ENDING)

    __stop_evt__            = False
    __msgid__               = 0
    __connected__           = False
    __initial_buffer_size__ = 1000
    __maximum_msg_size      = 1e7

    def __init__(self, sock, addr, factory):
        """
        :param sock: The client socket on which the protocol will run
        :param addr: The client address
        :param peerid: The peerid of the protocol
        """
        threading.Thread.__init__(self, name = "%s:%s" % (self.__class__.name, addr))

        self.transport      = sock
        self.addr           = addr
        self.factory        = factory

        self.__hdr_buffer__ = bytearray(self.__hdr_size__)
        self.__msg_buffer   = bytearray(self.__initial_buffer_size__)


    def run(self):
        """
        Thread receiving loop
        """
        factory         = self.factory
        self.factory    = None

        factory.connectedTCP(self)

        while not self.__stop_evt__:
            try:
                peerid, msgid, size = self.__recv_msg__()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Message Received [id : %s] [size : %d], [content : %s]" % \
                                    (str(peerid), size, str(self.__msg_buffer[:size])))
                factory.received(self, peerid, msgid, str(self.__msg_buffer[:size]))
            except (socket.timeout):
                pass
            except (socket.error, RuntimeError):
                break
            except (Exception):
                import traceback
                traceback.print_exc()

        self.transport.close()
        factory.disconnectedTCP(self)

    def stop(self):
        """
        This method shutdown the underlying socket.
        """
        self.transport.shutdown(socket.SHUT_RDWR)

    def getInfo(self):
        """
        """
        addr, port = self.transport.getsockname()
        return addr, port

    def getRemoteInfo(self):
        addr, port = self.transport.getpeername()
        return addr, port

    def __resize_buffer__(self, minimum_size):
        """
        Internal function that resize the internal message buffer to contain
        at least the number of bytes specified.

        :param minimum_size; The minimum buffer size in bytes
        """
        if logger.isEnabledFor(logging.INFO):
            logger.info("Resizing MSG input buffer size to [%d]" % new_buffer_size)

        self.__msg_buffer = bytearray(minimum_size)

    def __recv_msg__(self):
        """
        Internal method that received the BIP header and the following message
        This function block should block until the entire message is received.
        """
        # Receiving the Header
        recv_into_wait(self.transport, self.__hdr_buffer__, len(self.__hdr_buffer__))

        # Header parsing
        proto, peerid, msgid, size  = str(self.__hdr_buffer__).split()
        peerid                      = PeerID(peerid)
        size                        = int(size, 16)
        msgid                       = int(msgid, 16)

        if (self.__maximum_msg_size != 0) and (size > self.__maximum_msg_size):
            raise RuntimeError("Message size over limit ... discarding")

        # Resizing the buffer as needed
        if size > len(self.__msg_buffer):
            self.__resize_buffer__(size)

        # Receiving the actual message
        recv_into_wait(self.transport, self.__msg_buffer, size)

        return peerid, msgid, size


    def send(self, msg, peerid):
        """
        Encapsulate the msg with the bip header and send it through the
        transport

        :param msg: The actual message to send
        """
        size = len(msg)
        headers = BIP_HEADER_TEMPLATE % \
                        (self.__greeting_msg__, peerid,
                         self.__msgid__,  size)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Message Sent [id : %s] [size : %d], [content : %s]" % \
                            (str(peerid), size, msg))

        self.transport.sendall(''.join((headers, LINE_ENDING, msg)))
        self.__msgid__ += 1




class BIPFactory(object):
    timeout     = 5.0
    protocol    = BIPProtocol
    peerid      = PeerID(0)

    def __init__(self):
        self.peers          = {}
        self.pending_peers  = []
        self.lock           = threading.Lock()

    def build(self, sock, addr):
        """
        Called by the Reactor
        """
        sock.settimeout(self.timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        proto = self.protocol(sock, addr, self)

        with self.lock:
            self.pending_peers.append(proto)

        # Greeting Message
        proto.send("", self.peerid)
        proto.start()
        return proto

    def connected(self, proto, rpeerid):
        """
        Called by protocol
        """
        with self.lock:
            self.pending_peers.remove(proto)
            self.peers[rpeerid] = proto
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("TCP Connection Established with [%s]" % str(rpeerid))


    def disconnected(self, proto, rpeerid):
        """
        Called by protocol
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connection Closed with [%s]" % str(rpeerid))

    def disconnectedTCP(self, proto):
        """
        Called by protocol
        """
        with self.lock:
            for rpeerid in self.peers.keys():
                if proto == self.peers[rpeerid]:
                    del self.peers[rpeerid]
                    self.disconnected(proto, rpeerid)
            if proto in self.pending_peers:
                self.pending_peers.remove(proto)

    def connectionFailed(self, proto):
        """
        Called by protocol
        """
        proto.stop()
        if logger.isEnabledFor(logging.WARNING):
            logger.warning("BIP Handshake with %s [%d] has failed, Invalid"
                               "Protocol, closing connection..." % proto.getRemoteInfo())

    def connectedTCP(self, proto):
        """
        Should Eventually Use a Timer to disconnect when we did not
        received the connection initialization message in a correct
        amount of time.
        """
        def timeout_callback():
            if proto in self.pending_peers:
                self.connectionFailed(proto)


        reactor.Reactor().callLater(timeout_callback, self.timeout)


    def close(self, peerid = None):
        """
        This function close a connection with a peer. If peerid is not provided,
        close all remaining connections.

        :param peerid: The peerid
        """
        with self.lock:
            if peerid is None:
                for p in self.peers.keys():
                    self.peers[p].stop()
                for p in self.pending_peers:
                    p.stop()
                    self.pending_peers.remove(p)
            else:
                self.peers[peerid].stop()

    def getPeerInfo(self, peerid):
        """
        """
        with self.lock:
            return self.peers[peerid].getInfo()

    def received(self, proto, peerid, msgid, msg):
        if peerid not in self.peers:
            self.connected(proto, peerid)

    def __del__(self):
        with self.lock:
            for peer in self.peers.values():
                self.peers[peer].close()







