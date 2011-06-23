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
import select
import json

logger = logging.getLogger(__name__)

LINE_ENDING = "\r\n"
BIP_HEADER_TEMPLATE = "%s %s %.8x %.8x" + LINE_ENDING
BIP_GREETING_TIMEOUT = 1  # in seconds

DATAGRAM_MAXIMUM_SIZE = 2 ** 16

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
                                (__greeting_msg__, str(PeerID(0)), 0, 0))

    __stop_evt__            = False
    __msgid__               = 0
    __connected__           = False
    __initial_buffer_size__ = 1000
    __maximum_msg_size      = 1e8

    def __init__(self, sock, udpsock, factory):
        """
        :param sock: The client socket on which the protocol will run
        :param addr: The client address
        :param peerid: The peerid of the protocol
        """
        threading.Thread.__init__(self, name = "%s:%s[%d]" % ((self.__class__.name,) + sock.getpeername()))

        self.factory        = factory
        self.transportTCP   = sock
        self.transportUDP   = udpsock

        self.__hdr_buffer   = bytearray(DATAGRAM_MAXIMUM_SIZE)
        self.__msg_buffer   = bytearray(self.__initial_buffer_size__)

        self.lock           = threading.Lock()
        self.lost_count     = 0


    def __set_udp_transport(self, sock):
        self.transport_list = [self.transportTCP, sock]

    def __get_udp_transport(self):
        return self.transport_list[-1]

    transportUDP = property(__get_udp_transport, __set_udp_transport)


    def run(self):
        """
        Thread receiving loop
        """
        factory         = self.factory
        self.factory    = None

        factory.connectedTCP(self)

        while not self.__stop_evt__:
            transport_list = (self.transportTCP,) if self.transportUDP is None else (self.transportTCP, self.transportUDP)

            try:
                select_list = select.select(transport_list, [], [], 3)[0]
            except (select.error):
                break

            try:


                for transport in select_list:
                    recv_msg = self.__recv_msg_dgram if transport == self.transportUDP else self.__recv_msg
                    peerid, msgid, size, msg = recv_msg(transport)

                    if logger.isEnabledFor(logging.DEBUG):
                        proto = "TCP" if transport == self.transportTCP else "UDP"
                        logger.debug("Message Received through %s [id : %s] [size : %d], [content : %s]" % \
                                    (proto, str(peerid), size, msg))

                    factory.received(self, peerid, msgid, msg)
            except (socket.timeout):
                pass
            except (socket.error, RuntimeError):
                break
            except (Exception):
                import traceback
                traceback.print_exc()

        for transport in transport_list:
            transport.close()

        factory.disconnectedTCP(self)

        if logger.isEnabledFor(logging.INFO):
            logger.info("Transport Loop Ended")


    def stop(self):
        """
        This method shutdown the underlying socket.
        """
        for transport in [self.transportTCP, self.transportUDP]:
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except:
                pass

    def getInfo(self):
        """
        """
        addr, port = self.transportTCP.getsockname()
        return addr, port

    def getPeerInfo(self):
        addr, port = self.transportTCP.getpeername()
        return addr, port

    def __resize_buffer__(self, minimum_size):
        """
        Internal function that resize the internal message buffer to contain
        at least the number of bytes specified.

        :param minimum_size; The minimum buffer size in bytes
        """
        if logger.isEnabledFor(logging.INFO):
            logger.info("Resizing MSG input buffer size to [%d]" % minimum_size)

        self.__msg_buffer = bytearray(minimum_size)

    def __recv_msg_dgram(self, transport):
        size = transport.recv_into(self.__hdr_buffer, len(self.__hdr_buffer))
        if size == 0:
            raise socket.error()
        hdr = self.__hdr_buffer[:self.__hdr_size__]

        # Header parsing
        proto, peerid, msgid, size  = str(hdr).split()
        peerid                      = PeerID(peerid)
        size                        = int(size, 16)
        msgid                       = int(msgid, 16)


        return peerid, msgid, size, str(self.__hdr_buffer[self.__hdr_size__:size])



    def __recv_msg(self, transport):
        """
        Internal method that received the BIP header and the following message
        This function block should block until the entire message is received.
        """
        # Receiving the Header
        recv_bytes = transport.recv_into(self.__hdr_buffer, self.__hdr_size__)
        hdr = self.__hdr_buffer[:self.__hdr_size__]
        if self.__hdr_size__ != recv_bytes:
            raise RuntimeError("Invalid Header Detected")


        # Header parsing
        proto, peerid, msgid, size  = str(hdr).split()
        peerid                      = PeerID(peerid)
        size                        = int(size, 16)
        msgid                       = int(msgid, 16)


        # Resizing the buffer as needed
        realsize = size + len(LINE_ENDING)
        if realsize > len(self.__msg_buffer):
            self.__resize_buffer__(realsize)

        # Receiving the actual message
        recv_into_wait(transport, self.__msg_buffer, realsize)

        return peerid, msgid, size, str(self.__msg_buffer[:size])


    def send(self, msg, peerid, udp = False):
        """
        Encapsulate the msg with the bip header and send it through the
        transport

        :param msg: The actual message to send
        """
        self.lock.acquire()
        msgid = self.__msgid__
        self.__msgid__ += 1
        self.lock.release()

        size = len(msg)
        headers = BIP_HEADER_TEMPLATE % \
                        (self.__greeting_msg__, peerid,
                         msgid,  size)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Message Sent [id : %s] [size : %d, %s], [content : %s]" % \
                            (str(peerid), size, "UDP" if udp else "TCP", msg,))


        if udp:
            finalized_msg = ''.join((headers, msg, LINE_ENDING))
            self.transportUDP.send(finalized_msg)
        else:
            self.transportTCP.send(headers)
            self.transportTCP.sendall(msg)
            self.transportTCP.send(LINE_ENDING)






class BIPFactory(object):
    timeout     = 5.0
    protocol    = BIPProtocol
    peerid      = PeerID(0)

    def __init__(self):
        self.peers              = {}
        self.__unknown_peers    = []
        self.lock               = threading.Lock()

    def build_description(self):
        return {}

    def build(self, tcpsock, addr):
        """
        (Main Thread)
        """
        # TCP Socket Caracteristics
        tcpsock.settimeout(self.timeout)
        tcpsock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpsock.bind((socket.gethostname(), 0))

        udpport, addr = udpsock.getsockname()

        proto = self.protocol(tcpsock, udpsock, self)

        with self.lock:
            self.__unknown_peers.append(proto)

        # Greeting Message
        udpaddr, udpport = proto.transportUDP.getsockname()

        description = self.build_description()
        description['udp'] = udpport
        proto.send(json.dumps(description), self.peerid)
        proto.start()
        return proto


    def connected(self, proto, rpeerid):
        """
        (Protocol Thread)
        """
        with self.lock:
            self.__unknown_peers.remove(proto)
            self.peers[rpeerid] = proto
        if logger.isEnabledFor(logging.info):
            logger.info("TCP Connection Established with [%s]" % str(rpeerid))


    def disconnected(self, proto, rpeerid):
        """
        (Protocol Thread)
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Connection Closed with [%s]" % str(rpeerid))

    def disconnectedTCP(self, proto):
        """
        (Protocol Thread)
        """
        with self.lock:
            for rpeerid in self.peers.keys():
                if proto == self.peers[rpeerid]:
                    del self.peers[rpeerid]
                    self.disconnected(proto, rpeerid)
            if proto in self.__unknown_peers:
                self.__unknown_peers.remove(proto)

    def __timeout_callback(self, proto):
        with self.lock:
            """
            (Main Thread)
            """
            if proto in self.__unknown_peers:
                proto.stop()
                self.__unknown_peers.remove(proto)
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("BIP Handshake with %s [%d] has failed, after %ds "
                                   "closing connection..." % (proto.getPeerInfo() + (self.timeout,)))


    def connectedTCP(self, proto):
        """
        (Protocol Thread)
        Should Eventually Use a Timer to disconnect when we did not
        received the connection initialization message in a correct
        amount of time.

        :param proto: the protocol
        """
        def timeout_callback():
            self.__timeout_callback(proto)


        reactor.Reactor().callLater(timeout_callback, self.timeout)


    def close(self, peerid = None):
        """
        (Any Thread)
        This function close a connection with a peer. If peerid is not provided,
        close all remaining connections.

        :param peerid: The peerid
        """
        with self.lock:
            if peerid is None:
                for p in self.peers.keys():
                    self.peers[p].stop()
                for p in self.__unknown_peers:
                    p.stop()
                    self.__unknown_peers.remove(p)
            else:
                self.peers[peerid].stop()

    def getPeerInfo(self, peerid):
        """
        (Any Thread)

        :param peerid: the peerid we want the info from
        """
        return self.peers[peerid].getInfo()


    def received(self, proto, peerid, msgid, msg):
        """
        (Protocol Thread)

        :param proto: The protocol the message come from
        :param peerid: Peerid of the incomming msg
        :param msgid: The id of the message
        :param msg: The actual message
        """
        if peerid not in self.peers:
            proto.description = json.loads(msg)
            self.connected(proto, peerid)
            if "udp" not in proto.description:
                proto.transportUDP.close();
                proto.transportUDP = None
            else:
                addr, tcpport = proto.getPeerInfo()
                proto.transportUDP.connect((addr, proto.description['udp']))

            if logger.isEnabledFor(logging.INFO):
                logger.info("UDP %s on [%s]" % ("enable" if 'udp' in proto.description else "disabled",
                                                str(peerid)))





