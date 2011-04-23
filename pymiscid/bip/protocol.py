#
"""
This is the implementation of the BIP protocol based on twisted.
"""

import random
import logging
import threading
import weakref
import socket
import math


logger = logging.getLogger(__name__)

LINE_ENDING = "\r\n"
BIP_HEADER_TEMPLATE = "%s %s %.8x %.8x" + LINE_ENDING
BIP_GREETING_TIMEOUT = 1  # in seconds

class PeerID(int):
    """
    This class represent a peerid. Internally it is just a long int which with
    the method str always givin the hexadecimal value at the right length that
    is defined in the BIP Protocol.
    """
    __slots__ = []
    def __new__(cls, val = None):
        if val is None:
            val = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFF00
        elif isinstance(val, str):
            val = long(val, 16)
        return int.__new__(cls, val)

    def __str__(self):
        return "%08.x" % self

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

def peerid_generator_factory(base = None):
    """
    A small generator which generate peerids for a service.
    """
    pid = PeerID(base)
    for i in xrange(256):
        yield pid
        pid += 1


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
    __name__ = 'BIP'
    __version__ = '1.0'
    __greeting_msg__ = "%s/%s" % (__name__, __version__)
    __hdr_size__ = len(BIP_HEADER_TEMPLATE %
                         (__greeting_msg__, str(PeerID(0)), 0, 0)) \
                            + len(LINE_ENDING)

    __stop_evt__ = False
    __msgid__ = 0
    __connected__ = False
    __initial_buffer_size__ = 1000

    def __init__(self, sock, addr, factory):
        """
        :param sock: The client socket on which the protocol will run
        :param addr: The client address
        :param peerid: The peerid of the protocol
        """
        threading.Thread.__init__(self)
        self.transport = sock
        self.addr = addr
        self.factory = weakref.ref(factory)

        self.__hdr_buffer__ = bytearray(self.__hdr_size__)
        self.__msg_buffer__ = bytearray(self.__initial_buffer_size__)


    def run(self):
        """
        Thread receiving loop
        """
        while not self.__stop_evt__:
            try:
                peerid, msgid, size = self.__recv_msg__()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Message Received [id : %s] [content : %s]" % \
                                    (str(peerid), str(self.__msg_buffer__[:size])))
                self.factory().received(self, peerid, msgid, str(self.__msg_buffer__[:size]))
            except (socket.timeout, e):
                pass
            except (socket.error, e):
                break
            except (RuntimeError, e):
                break
            except (Exception, e):
                import traceback
                traceback.print_exc()

        self.transport.close()
        self.factory().disconnectedTCP(self)

    def stop(self):
        """
        This method shutdown the underlying socket.
        """
        self.transport.shutdown(socket.SHUT_RDWR)


    def __resize_buffer__(self, minimum_size):
        """
        Internal function that resize the internal message buffer to contain
        at least the number of bytes specified.

        :param minimum_size; The minimum buffer size in bytes
        """
        mult = 2 ** int(math.ceil(math.log(minimum_size / float(len(self.__msg_buffer__)), 2)))
        new_buffer_size = len(self.__msg_buffer__) * mult

        if logger.isEnabledFor(logging.INFO):
            logger.info("Resizing MSG input buffer size to [%d]" % new_buffer_size)

        self.__msg_buffer__ = bytearray(new_buffer_size)

    def __recv_msg__(self):
        """
        Internal method that received the BIP header and the following message
        This function block should block until the entire message is received.
        """
        # Receiving the Header
        recv_into_wait(self.transport, self.__hdr_buffer__, len(self.__hdr_buffer__))

        # Header parsing
        proto, peerid, msgid, size = str(self.__hdr_buffer__).split()
        peerid = PeerID(peerid)
        size = int(size, 16)
        msgid = int(msgid, 16)

        # Resizing the buffer as needed
        if size > len(self.__msg_buffer__):
            self.__resize_buffer__(size)

        # Receiving the actual message
        recv_into_wait(self.transport, self.__msg_buffer__, size)

        return peerid, msgid, size


    def send(self, msg, peerid):
        """
        Encapsulate the msg with the bip header and send it through the
        transport

        :param msg: The actual message to send
        """
        headers = BIP_HEADER_TEMPLATE % \
                        (self.__greeting_msg__, peerid,
                         self.__msgid__,  len(msg))
        self.transport.sendall(''.join([headers, LINE_ENDING, msg]))
        self.__msgid__ += 1




class BIPFactory(object):
    timeout = 5.0
    protocol = BIPProtocol

    def __init__(self, peerid):
        self.peerid = PeerID(peerid)
        self.peers = {}

    def build(self, sock, addr):
        sock.settimeout(self.timeout)
        proto = self.protocol(sock, addr, self)
        proto.send("", self.peerid)
        proto.start()
        return proto

    def connected(self, proto, rpeerid):
        self.peers[rpeerid] = proto

    def disconnected(self, proto, rpeerid):
        pass

    def disconnectedTCP(self, proto):
        todelete = []
        for rpeerid in self.peers:
            if proto == self.peers[rpeerid]:
                todelete.append(rpeerid)
                self.disconnected(proto, rpeerid)
        for rpeerid in todelete:
            del self.peers[rpeerid]


    def received(self, proto, peerid, msgid, msg):
        if peerid not in self.peers:
            self.connected(proto, peerid)







