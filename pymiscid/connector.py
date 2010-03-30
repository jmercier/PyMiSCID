# Copyright (c) 2009 J-Pascal Mercier
"""
This is
"""
import logging
import threading
import weakref

from bip.factory import BIPFactory
from bip.protocol import UNBOUNDED_PEERID, Peerid
from twisted.internet import reactor
from twisted.application import service

from dispatcher import BasicEventDispatcher, ControlEventDispatcher

import codebench.generator as generator

from cstes import XML_IO_CONNECTOR_TAG, \
                  XML_I_CONNECTOR_TAG, \
                  XML_O_CONNECTOR_TAG, \
                  UNBOUNDED_CONNECTOR_NAME, \
                  CONNECTION_TIMEOUT, \
                  CONTROL_ANSWER, \
                  CONTROL_EVENT, \
                  CONTROL_QUERY, \
                  TXT_SEPARATOR, \
                  IO_CONNECTOR_PREFIX, \
                  INPUT_CONNECTOR_PREFIX, \
                  OUTPUT_CONNECTOR_PREFIX

logger = logging.getLogger(__name__)


INPUT, OUTPUT, INOUTPUT = range(3)

xml_tag_to_connector_type_map = { XML_IO_CONNECTOR_TAG : INOUTPUT,
                                  XML_I_CONNECTOR_TAG : INPUT, 
                                  XML_O_CONNECTOR_TAG : OUTPUT }

connector_type_to_xml_tag_map = { INOUTPUT : XML_IO_CONNECTOR_TAG,
                                  INPUT : XML_I_CONNECTOR_TAG , 
                                  OUTPUT : XML_O_CONNECTOR_TAG   }
txt_to_connector_type_map = {'o' : OUTPUT,
                             'd' : INOUTPUT,
                             'i' : INPUT }

class BIPPrimalConnector(object):
    """
    This object is the primal ProtocolFactory observer. It is intendended to
    received direct event from the protocol. This call is in the same thread as
    the transport so this is supposed to be quick and succint.
    """
    dispatcher = None
    peerid = None
    def __init__(self):
        """
        PeerId  dict initialisation
        """
        self.peers = {}

    def __hash__(self):
        return self.peerid

    def connected(self, protocol):
        """
        This is a direct callback from the protocol object. This call is
        forwarded to the dispatcher in a thread from the threadpoolu.
        """
        peerid = protocol.rpeerid
        if peerid in self.peers:
            if logger.isEnabledFor(logging.CRITICAL): 
                logger.critical("Peer Collision Detected : Dictionary Tainted")
        else:
            self.peers[peerid] = protocol
            if self.dispatcher is not None:
                self.dispatcher.connectedEvent(protocol.rpeerid)

    def disconnected(self, protocol):
        """
        This is a direct callback from the protocol object. This call is
        forwarded to the dispatcher in a thread from the threadpool.
        """
        if protocol.rpeerid in self.peers:
            del self.peers[protocol.rpeerid]
        if self.dispatcher is not None:
            self.dispatcher.disconnectedEvent(protocol.rpeerid)

    def received(self, msg):
        """
        This is a direct callback from the protocol object. This call is
        forwarded to the dispatcher in a thread from the threadpool. The 
        """
        if self.dispatcher is not None:
            reactor.callInThread(self.dispatcher.receivedEvent, msg)

    def __connect__(self, proxy):
        reactor.connectTCP(proxy.host, int(proxy.tcp), self.protocol_factory)


    def __disconnect__(self, peerid):
        protocol = self.peers.get(peerid, None)
        if protocol is not None: 
            protocol.transport.loseConnection()
            if logger.isEnabledFor(logging.DEBUG): 
                logger.debug("Disconnect client : %s" % str(peerid))

    def __loseConnection__(self, peerid = None):
        """
        This method close every connection with every peers
        """
        if peerid is None:
            for peer in self.peers.itervalues():
                peer.transport.loseConnection()
                self.dispatcher.disconnectedEvent(peer.rpeerid)
        else:
            try:
                self.peers[peerid].loseConnection()
            except KeyError:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Cannot close connection to unconnected peer")


    def peersCount(self):
        """
        This methods returns the number of connected peers.
        """
        return len(self.peers)



    def __send__(self, msg, peerid = None):
        """
        This function is intended to be call from the main thread. Same
        description as send method. 
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Message sent through %s : %s" % (self.peerid, msg))

        string_msg = str(msg)
        if peerid is None:
            for peer in self.peers.itervalues():
                peer.send(string_msg)
        elif peerid in self.peers:
            self.peers[peerid].send(string_msg)
        else:
            if logger.isEnabledFor(logging.WARNING): 
                logger.warning("Trying to send msg to an unknown peer -- %s --"
                               % str(peerid))


class Connector(BIPPrimalConnector, service.Service):
    """
    This object is the standard for a Input/Output connector, A two way network
    pipeline type object. This object is also intended to make the bridge
    between main thread protocol and threaded callback. Method starting en
    ending with __ are to be called from the main thread and others from any
    thread.
    """
    name = UNBOUNDED_CONNECTOR_NAME
    protocol_factory_type = BIPFactory
    peerid = UNBOUNDED_PEERID

    protocol_factory = None
    tcp = None
    udp = 0
    sbind = None

    txt_prefix = IO_CONNECTOR_PREFIX

    xml_tag = XML_IO_CONNECTOR_TAG
    xml_attributes = ['name']
    xml_childs = ['tcp', 'description', 'peerId', 'peers']

    def __set_peerid__(self, value):
        self.peerid = value
    def __get_peerid__(self):
        return self.peerid
    peerId = property(__get_peerid__, __set_peerid__) # STUPID OMISCID NAME

    def __init__(self, description = "Unknown Description"):
        """
        Init
        """
        super(Connector, self).__init__()

        self.description = description
        self.dispatcher = BasicEventDispatcher()
        self.connected_events = {}

    def __init_factory__(self):
        """
        This is a last minute factory instanciation. This is called before a
        connection is made and before the service is started. It instanciate
        protocol_factory of the type defined in the variable
        protocol_factory_type
        """
        self.protocol_factory = self.protocol_factory_type()
        self.protocol_factory.service = weakref.proxy(self)

    def connect(self, proxy, timeout = CONNECTION_TIMEOUT):
        """
        This method connect the current connector to a remote connector defined
        by the address and the port. In the case the parameter async is False,
        when this function returns, we can conclude the connection is made.
        Else, we can't say anything.
        """
        if self.protocol_factory is None:
            self.__init_factory__()

        # This connector is already connected, returns
        if proxy.peerid in self.peers:
            return 

        if (proxy.peerid in self.connected_events):
            evt = self.connected_events[proxy.peerid]
        else:
            evt = threading.Event()
            self.connected_events[proxy.peerid] = evt
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Connecting to %s(%s) on port %d" 
                         % (proxy.host, proxy.addr, int(proxy.tcp)))

        reactor.callFromThread(self.__connect__, proxy)
        self.connected_events[proxy.peerid].wait(timeout)
        if not evt.isSet(): 
            if logger.isEnabledFor(logging.WARNING): 
                logger.warning("Connection Timed Out -- %s --" 
                               % str(proxy.peerid))
            raise RuntimeError("Connection timeout reached")

    def disconnect(self, peerid):
        """
        This is the thread safe version of __dictonnect__
        """
        reactor.callFromThread(self.__disconnect__, peerid)

    def connected(self, protocol):
        """
        This is an override for the primal connector protocol callback to ensure
        we fire the connected event if the connection from the right peerid is
        received.
        """
        peerid = protocol.rpeerid

        if logger.isEnabledFor(logging.INFO):
            logger.info("connection from %s to local connector %s "
                        % (str(peerid), self.name))
        BIPPrimalConnector.connected(self, protocol)
        evt = self.connected_events.pop(peerid, None)
        if evt is not None: 
            evt.set()

    def startService(self):
        """
        This method inherit from the twisted.service.Service. It build the and
        start the service.
        """
        service.Service.startService(self)
        if self.protocol_factory is None:
            self.__init_factory__()
        self.sbind = reactor.listenTCP(0, self.protocol_factory)
        self.tcp = self.sbind.getHost().port
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Starting Connector on port : %d" % (self.tcp))

    def __stopService__(self):
        service.Service.stopService(self)
        self.sbind.stopListening()
        self.__loseConnection__()
        self.sbind = None
        self.tcp = 0
        self.udp = 0

    def stopService(self):
        """
        This method stop the connector service.
        """
        reactor.callFromThread(self.__stopService__)

    def loseConnection(self, peerid = None):
        """
        Callback from the low level protocol. Called when we lose connection for
        an unknow reason.
        """
        reactor.callFromThread(self.__loseConnection__, peerid)

    def send(self, msg, peerid = None):
        """
        This method is intended to be called from am outside thread. It prepare
        the message for the protocol object and ensure the transport is used in
        the main thread.
        """
        reactor.callFromThread(self.__send__, msg, peerid = peerid)

    __call__ = send

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


class IConnector(Connector):
    """
    This Class is intend to restric the output possibilities of an Input only
    connector.
    """
    txt_prefix = INPUT_CONNECTOR_PREFIX
    xml_tag = XML_I_CONNECTOR_TAG
    def send(self, msg, peerid = None):
        """
        Raise an Exception.
        """
        if logger.isEnabledFor(logging.WARNING): 
            logger.warning("Trying to send msg through an Input Only Connector")
        raise RuntimeError("Sending msg through an Input Connector")

    def connect(self, proxy, timeout = CONNECTION_TIMEOUT):
        """
        Verify the proxy is not another input connector which do not make any
        sense
        """
        if proxy.type == INPUT:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Trying to connect 2 input connector toghether")
            raise RuntimeError("Connecting connector of wrong type")
        else:
            return Connector.connect(self, proxy, timeout = timeout)


class OConnector(Connector):
    """
    This Class is intend to restrict the input possibilities of an Output
    connector.
    """
    txt_prefix = OUTPUT_CONNECTOR_PREFIX
    xml_tag = XML_O_CONNECTOR_TAG
    def received(self, msg):
        """
        Override the received function. Close connection on the client which
        tries to send something to an output connector. Bad client ...
        """
        if logger.isEnabledFor(logging.WARNING): 
            logger.warning("Receiving msg : Output Only Connector <closing>")
        if msg.peerid in self.peers:
            self.peers[msg.peerid].transport.loseConnection()

    def connect(self, proxy, timeout = CONNECTION_TIMEOUT):
        """
        Verify the proxy is not another output connector which does not make any
        sense.
        """
        if proxy.type == OUTPUT:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Trying to connect 2 output connector toghether")
            raise RuntimeError("Connecting connector of wrong type")
        else:
            return Connector.connect(self, proxy, timeout = timeout)


class ControlConnector(Connector):
    """
    This Class is the implemenetation of the control connector. It implement all
    standard connector method plus it is designed to send event, answer and
    query
    """
    name = "control"
    def __init__(self):
        """
        Initialisation of the generator and the ControlDispatcher()
        """
        self.qid_generator = generator.uid_generator()
        Connector.__init__(self)
        self.dispatcher = ControlEventDispatcher()
        self.dispatcher.control = weakref.ref(self)

    def query(self, msg, peerid):
        """
        This method send a control query to the given peerid ( only if the connection
        is already active) and encapsulate the msg. This method returns a
        defered which fires when the answer is received.
        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Sending Query ... to %s" % str(peerid))
        qid = self.qid_generator.next()
        answer = self.dispatcher.addWaitingAnswer(qid, peerid)
        self.send(CONTROL_QUERY % (qid, msg), peerid = peerid)
        return answer

    def answer(self, msg, qid, peerid):
        """
        This method is called to answer a particular query. It encapsulate the
        msg in the right header for the dispatch.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending Answer ... to %s" % str(peerid))
        self.send(CONTROL_ANSWER % (qid, msg), peerid = peerid)

    def event(self, msg, peerid):
        """
        This method is called to send an event to a particular peerid. It
        encapsulate the msg in the right header for the dispatch.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending Event ... to %s" % str(peerid))
        self.send(CONTROL_EVENT % (msg), peerid = peerid)


class ConnectorProxy(object):
    """
    This object represent a remote connector. It does nothing, it is just an
    container of some properties.
    """
    xml_updatable = ['description', 'tcp', 'udp', 'peerId', 'peers', 'require']

    __peerid__ = None
    __tcp__ = None
    __udp__ = None
    __peers__ = []

    def __set_type__(self, value):
        if value in xml_tag_to_connector_type_map:
            self.__type__ = xml_tag_to_connector_type_map[value]
        elif value in txt_to_connector_type_map:
            self.__type__ = txt_to_connector_type_map[value]
        else:
            self.__type__ = value
    def __get_type__(self):
        return self.__type__
    type = property(__get_type__, __set_type__)

    def __get_xml_type__(self):
        return connector_type_to_xml_tag_map[self.__type__]
    xml_type = property(__get_xml_type__)

    def __get_peers__(self):
        return self.__peers__
    def __set_peers__(self, value):
        if value in [None, '', 'None']:
            value = []
        elif isinstance(value, dict):
            value = [Peerid(p['id']) for p in value['peer']]
        self.__peers__ = value
    peers = property(__get_peers__, __set_peers__)

    def __init__(self, name, addr):
        """
        """
        super(ConnectorProxy, self).__init__()
        self.name = name
        self.addr = addr

    def __get_tcp__(self): 
        return self.__tcp__
    def __set_tcp__(self, val): 
        self.__tcp__ = None if val in [None, 'None'] else int(val)
    tcp = property(__get_tcp__, __set_tcp__)

    def __set_peerid__(self, val): 
        self.__peerid__ = Peerid(val)
    def __get_peerid__(self): 
        return self.__peerid__
    peerid = property(__get_peerid__, __set_peerid__)
    peerId = peerid

    def __set_udp__(self, val): 
        self.__udp__ = None if val in [None, 'None'] else int(val)
    def __get_udp__(self):  
        return self.__udp__
    udp = property(__get_udp__, __set_udp__)


__unbound_control__ = ControlConnector()
__unbound_control__.peerid = Peerid()


