#
"""
This module is intended to describe the dispatcher for connector events
"""
import logging
import weakref
from twisted.internet import reactor, defer
import codebench.events
import codebench.xml
from lxml import etree

from cstes import QUERY_TIMEOUT, \
                  CONTROL_EVENT_TAG, \
                  CONTROL_ANSWER_TAG, \
                  CONTROL_QUERY_TAG, \
                  VARIABLE_TAG, \
                  FULLDESC_TAG, \
                  SUBSCRIBE_TAG, \
                  UNSUBSCRIBE_TAG, \
                  INPUT_CONNECTOR_TAG, \
                  OUTPUT_CONNECTOR_TAG, \
                  IO_CONNECTOR_TAG, \
                  VARIABLE_EVENT_MSG

from bip.protocol import PeerError, Peerid

logger = logging.getLogger(__name__)


class BasicEventDispatcher(codebench.events.ThreadsafeEventDispatcher):
    """
    This object is the basic event dispatcher for the three standards connector
    events.
    """
    events = ['connected', 'disconnected', 'received']


class ControlEventDispatcher(BasicEventDispatcher):
    """
    This object is a special observer for the ControlConnector which dispatch
    the event to the connector service.
    """
    __qtimeout__ = QUERY_TIMEOUT
    service = None
    control = None

    def __init__(self):
        BasicEventDispatcher.__init__(self)
        self.deferred_answers = {}
        self.remote_observers = {}
        self.proxys = {}
        self.oid = self.addObserver(self)

    def __del__(self):
        self.removeObserver(self.oid)

    def __query_timedout__(self, qid, peerid):
        """
        This is an internal method that ensure we receive an answer for the
        query in an acceptable time.
        """
        if qid in self.deferred_answers[peerid]:
            if logger.isEnabledFor(logging.WARNING): 
                logger.warning("Answer Timeout :  qid %08.x, peer %s" % 
                                    (qid, peerid))
            answer = self.deferred_answers[peerid].pop(qid)
            answer.errback(PeerError(peerid, 'Answer Timout'))

    def addProxy(self, proxy):
        """
        TO BE REMOVED
        """
        self.proxys[proxy.peerid] = weakref.ref(proxy)

    def removeProxy(self, proxy):
        """
        TO BE REMOVED. 
        """
        self.proxys.pop(proxy.peerid, None)

    def addWaitingAnswer(self, qid, peerid):
        """
        This method is ussed to create the defered object and add the it
        to the waiting list. This method is normally called by the connector
        when a query is made to create the right defered and to return it to
        the caller.
        """
        answer  = defer.Deferred()
        self.deferred_answers[peerid][qid] = answer
        reactor.callLater(self.__qtimeout__, self.__query_timedout__,  qid,
                          peerid)
        return answer

    def connected(self, peerid):
        """
        Callback from the connector.
        """
        self.deferred_answers[peerid] = {}
        self.remote_observers[peerid] = {}

    def disconnected(self, peerid):
        """
        Callback from the connector.
        """
        while len(self.deferred_answers[peerid]) != 0:
            qid, deferred = self.deferred_answers[peerid].popitem()
            deferred.errback(RuntimeError("Connection Lost"))
        while len(self.remote_observers[peerid]) != 0:
            vname, oid = self.remote_observers[peerid].popitem()
            var = self.service().variables[vname]
            var.removeObserver(peerid)

    def __dispatch_variable_query__(self, root, msg):
        """
        This method dispatch the variable query to the underlying service.
        """
        vname = root.attrib['name']
        var = self.service().variables[vname]
        if len(root.getchildren()) != 0:
            codebench.xml.Marshall.update(var, root)
        return codebench.xml.Marshall.dumps(var)

    def __dispatch_connector_query__(self, root, msg):
        """
        """
        cname = root.attrib['name']
        con = self.service().connectors[cname]
        return codebench.xml.Marshall.dumps(con)

    def __dispatch_subscribe_query__(self, root, msg):
        """
        """
        vname = root.attrib['name']
        var = self.service().variables[vname]
        if vname not in self.remote_observers[msg.peerid]:
            var.addObserver(self.variableChanged, var.name, msg.peerid, oid = msg.peerid)
            self.remote_observers[msg.peerid][vname] =  msg.peerid
        else:
            logger.warning("Multiple variable subscriptio [%s] to var - %s -" 
                           % (str(msg.peerid), vname))
        return codebench.xml.Marshall.dumps(var)

    def __dispatch_unsubscribe_query__(self, root, msg):
        """
        """
        vname = root.attrib['name']
        var = self.service().variables[vname]
        if vname in self.remote_observers[msg.peerid]:
            var.removeObserver(self.remote_observers[msg.peerid][vname])
            del self.remote_observers[msg.peerid][vname]
        if len(self.remote_observers[msg.peerid]) == 0:
            self.control().disconnect(msg.peerid)

    def __dispatch_description_query__(self, root, msg):
        """
        """
        return self.service().XMLDescription()

    def dispatchQuery(self, root, msg):
        """
        This method is called to dispatch a query type of msg.

        """
        if logger.isEnabledFor(logging.DEBUG): 
            logger.debug("Query Received " + msg.data)

        if self.service is not None:
            real_query = root.getchildren()[0]
            qid = int(root.attrib['id'], 16)
            try:
                answer = self.query_dispatch_table[real_query.tag](self, real_query, msg)
                if answer is not None:
                    self.control().answer(answer, qid, msg.peerid)
            except KeyError, err:
                if logger.isEnabledFor(logging.WARNING): 
                    logger.warning('Unknown Control Type (%s): peerid %08.x' 
                                   % (root.tag, msg.peerid))
                logger.exception(str(err))

    def dispatchEvent(self, root, msg):
        """
        This method is called to dispatch an event type of msg
        """
        real_event = root[0]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Query Event")
        if msg.peerid not in self.proxys:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Received event for an unknown proxy : %s"
                               % str(msg.peerid))
        else:
            vname = real_event.attrib['name']
            proxy = self.proxys[msg.peerid]()
            codebench.xml.Marshall.update(proxy.variables[vname], real_event)

    def dispatchAnswer(self, root, msg):
        """
        This method is intended to dispatch the answer for a query.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Query Answer")
        qid = Peerid(root.attrib['id'])
        if qid in self.deferred_answers[msg.peerid]:
            answer = self.deferred_answers[msg.peerid].pop(qid)
            answer.callback(root.getchildren())
        else:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning('UnRequested or TimedOut Answer : qid.%08.x' 
                               % qid)

    def received(self, msg):
        """
        This method is the main dispatcher for the types of query defined by the
        root tag of the xml tree.
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("ctrl msg received <%d>: %s" % (msg.peerid, msg.data))
        root = etree.fromstring(msg.data)
        try:
            self.dispatch_table[root.tag](self, root, msg)
        except KeyError, err:
            if logger.isEnabledFor(logging.WARNING): 
                logger.warning('Unknown Control Type (%s): peerid %08.x' 
                               % (root.tag, msg.peerid))

    def variableChanged(self, value, name, peerid):
        """
        This is a callback from the variable when we have remote observer. This
        event is to be dispatched away...
        """
        self.control().event(VARIABLE_EVENT_MSG % (name, value), peerid)

    dispatch_table = {CONTROL_EVENT_TAG : dispatchEvent,
                      CONTROL_ANSWER_TAG : dispatchAnswer,
                      CONTROL_QUERY_TAG : dispatchQuery }

    query_dispatch_table = {VARIABLE_TAG: __dispatch_variable_query__,
                            FULLDESC_TAG : __dispatch_description_query__,
                            SUBSCRIBE_TAG : __dispatch_subscribe_query__,
                            UNSUBSCRIBE_TAG : __dispatch_unsubscribe_query__,
                            INPUT_CONNECTOR_TAG : __dispatch_connector_query__,
                            OUTPUT_CONNECTOR_TAG : __dispatch_connector_query__,
                            IO_CONNECTOR_TAG : __dispatch_connector_query__}


