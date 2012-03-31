#
"""
This is the implementation of the BIP protocol based on twisted.
"""
from twisted.internet import reactor, protocol

try:
    from ..codebench import events
except Exception, err:
    from codebench import events

import random
import logging
import ctypes

logger = logging.getLogger(__name__)

LINE_ENDING = "\r\n"
BIP_HEADER_TEMPLATE = "%s %s %.8x %.8x" + LINE_ENDING
BIP_GREETING_TIMEOUT = 1  # in seconds

class Peerid(long):
    """
    This class represent a peerid. Internally it is just a long int which with
    the method str always givin the hexadecimal value
    """
    __slots__ = []
    def __new__(cls, val = None):
        if val is None:
            val = random.randint(0, 0xFFFFFFFF) & 0xFFFFFFFF00
        elif isinstance(val, str):
            val = long(val, 16)
        return long.__new__(cls, val)

    def __str__(self):
        return "%08.x" % self

    def __add__(self, val):
        return Peerid(val + self)

    def __sub__(self, val):
        return Peerid(val - self)

    def base(self):
        """
        This method returns the peerid of the service for the given peerid
        """
        return Peerid(self & 0xFFFFFFFF00)

    def __getid__(self):
        return self
    id = property(__getid__)


def peerid_generator_factory():
    """
    A small generator which generate peerids for a service.
    """
    pid = Peerid()
    for i in xrange(256):
        yield pid
        pid += 1

UNBOUNDED_PEERID = Peerid(0xFFFFFFFF)

class MessageBuilder(object):
    """
    This class contains all the necessary information about the message from
    another peer. It also helps the build process from splitted msg.
    """
    def __init__(self, peerid, msgid, rlen, host):
        """
        Initialisation to keep header information for further needs
        """
        self.peerid = peerid
        self.msgid = msgid
        self.rlen = rlen
        self.host = host
        self.buffer = (ctypes.c_char * (rlen - 2))()

    def __get_data__(self):
        return self.buffer.raw
    data = property(__get_data__)

    def build(self, data):
        """
        This method keep a pointer to the data and join all buffers
        when we received all the required data.
        """
        if self.rlen == 0:
            raise Exception("Message Finished")

        data, rest = data[:self.rlen], data[self.rlen:]
        datalen = len(data)

	#print "rlen=%d, datalen=%d" %(self.rlen,datalen)

        if datalen == 2:
            pass
	elif self.rlen == datalen:
            self.buffer[-(self.rlen - 2):] = data[:-2]
        elif (self.rlen - 2) <= datalen:
            self.buffer[-(self.rlen - 2):] = data
        else:
            self.buffer[-(self.rlen - 2):-(self.rlen - 2) + datalen] = data
        self.rlen -= datalen
        return rest

    def __str__(self):
        return self.data

class FastLineReceiver(protocol.Protocol):
    """
    This is a reimplementation of the twisted LineReceiver. This
    implementation take for granted we know the size of the header 
    beforehand so we can skip the parsing phase and split the buffer 
    directly. This object do not wait for the next message to restart 
    the state machine so it should have lower latency for small tcp
    packet. For very small packet with a the Nagle algorithm since 
    """
    line_length = 0
    line_mode = True
    __line_buffer = None
    __line_rlen = 0

    def setLineMode(self):
        """
        This function set the receiver mode to line mode and process
        the data.
        """
        self.line_mode = True

    def setRawMode(self):
        """
        This function set the receiver mode to raw mode and process
        the data.
        """
        self.line_mode = False

    def _dataReceived(self, data):
        rest = ""
        if self.line_mode:
            if self.__line_rlen == 0:
                self.__line_buffer = []
                self.__line_rlen = self.line_length
            hdr, rest = data[:self.__line_rlen], data[self.__line_rlen:]
            self.__line_rlen -= len(hdr)
            self.__line_buffer.append(hdr)
            if self.__line_rlen == 0:
                self.lineReceived(''.join(self.__line_buffer))
                self.setRawMode()
        else:
            rest = self.rawDataReceived(data)
        return rest



    def dataReceived(self, data):
        """
        This function append data to a buffer if until we have at least
        line_size and then call lineReceived. Then , it switches to 
        RawDataMode.
        """
        while len(data) != 0:
                data = self._dataReceived(data)

    def lineReceived(self, data):
        """
        Empty callback
        """
        pass

    def rawDataReceived(self, data):
        """
        Empty callback
        """
        pass

class BIPBaseProtocol(FastLineReceiver, events.EventDispatcherBase):
    """
    This class is the main implementation of the BIP Protocol.
    """
    __msg__ = None
    __msgid__ = None
    rpeerid = None

    __name__ = 'BIP'
    __version__ = '1.0'
    __greeting__ = "%s/%s" % (__name__, __version__)
    line_length = len(BIP_HEADER_TEMPLATE % 
                      (__greeting__, str(Peerid(0)), 0, 0))

    __raw_mode__ = False

    events = ['connected', 'disconnected', 'received']

    def rawDataReceived(self, data):
        """
        We are in the process of receiving a message, we accumulate the data
        structures through the MessageBuilder.
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Raw Data Received")
        rest = self.__msg__.build(data)
        if self.__msg__.rlen == 0:
            if self.__msg__.msgid == 0:
                self.rpeerid = self.__msg__.peerid
                if logger.isEnabledFor(logging.DEBUG):
                    logger.info("HandShake Successful with %s" % (self.rpeerid))
                self.connectedEvent(self)
            else:
                # not sure about this optimization
                optimized_size = max(len(self.__msg__.data) / 10 , 65535)
                if (self.transport.bufferSize > (optimized_size * 2)) or (self.transport.bufferSize < (optimized_size / 2)):
                    self.transport.bufferSize = optimized_size
                self.receivedEvent(self.__msg__)
            self.setLineMode()
        return rest

    def lineReceived(self, line):
        """
        We received a line, the bip header, we process the msg accordingly.
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Line Data Receive")
        proto, peerid, msgid, size = line.split()
        peerid = Peerid(peerid)
        size = int(size, 16)
        msgid = int(msgid, 16)
        if (msgid == 0) and (proto != self.__greeting__):
            self.transport.loseConnection()
            return

        self.__msg__ = MessageBuilder(peerid, msgid, size + len(LINE_ENDING),
                                      self.host)

    def send(self, msg):
        """
        Encapsulate the msg with the bip header and send it through the 
        transport
        """
        headers = BIP_HEADER_TEMPLATE % \
                        (self.__greeting__, self.factory.service.peerid,
                         self.__msgid__,  len(msg))
        self.transport.write(''.join([headers, msg, LINE_ENDING]))
        self.__msgid__ += 1

    def connectionMade(self):
        """
        Setting the tcpNoDelay since we want to limit the latency and 
        setting the callback for the handshake timeout
        """
        self.transport.setTcpNoDelay(True)
        self.host = self.transport.getPeer().host
        if logger.isEnabledFor(logging.INFO):
            logger.info("Connection made : %s, starting handshake procedure" %
                                            self.host)
        self.__msgid__ = 0 
        self.send("")

        reactor.callLater(self.factory.timeout, self.handshake_timeout)

    def handshake_timeout(self):
        """
        Checking if we received the handshake packet. In the negative, 
        we close the transport.
        """
        if self.rpeerid is None:
            if logger.isEnabledFor(logging.INFO): 
                logger.info("No answer, closing connection")
            self.transport.loseConnection()

    def connectionLost(self, reason):
        """
        The connection is lost, we just forward the call to the service
        """
        if logger.isEnabledFor(logging.INFO):
            logger.info("Client Connection Lost -- %s --" % self.host)
        if self.rpeerid is not None:
            self.disconnectedEvent(self)

class PeerError(Exception):
    """
    A simple exception with the peerid.
    """
    def __init__(self, peerid, msg = ""):
        Exception.__init__(self, msg)
        self.peerid = peerid




