#
"""
This module add defines every Service objects necessary for OMiSCID.
"""
from __future__ import with_statement
import logging
import weakref
import copy

import variable, connector
import codebench.generator as generator
import codebench.xml as xml

from twisted.application import service
from twisted.internet import threads, reactor
from bonjour import BonjourServicePublisher

from bip.protocol import Peerid, peerid_generator_factory

from cstes import DESCRIPTION_VARIABLE_NAME, \
                  FULL_DESCRIPTION_VALUE, \
                  SERVICE_FULL_DESCRIPTION, \
                  VARIABLE_TAG, \
                  OMISCID_DOMAIN, \
                  VARIABLE_EVENT_MSG, \
                  REQUEST_CONTROL_QUERY, \
                  VARIABLE_SUBSCRIBE, \
                  VARIABLE_UNSUBSCRIBE, \
                  PROXY_DISCONNECT_TIMEOUT

logger = logging.getLogger(__name__) 

class ServiceCommon(object):
    """
    This class is the base of every service around. Even the evil ServiceProxy
    """
    control = connector.__unbound_control__

    peerid = None

    def __init__(self):
        """
        Simple Variable and Connectors dict init
        """
        self.variables = {}
        self.connectors = {}

    def __hash__(self):
        return self.peerid

    def addVariableObserver(self, vname, callback, *args):
        """
        Add an observer for a variable. returns an id to remove the callback
        """
        return self.variables[vname].valueEvent.addObserver(callback, *args)

    def removeVariableObserver(self, vname, cid):
        """
        remove an observer from a variable callback
        """
        self.variables[vname].valueEvent.removeObserver(cid)

    def __getattr__(self, name):
        if name in self.variables:
            res = self.variables[name]
        elif name in self.connectors:
            res = self.connectors[name]
        else:
            res = object.__getattribute__(self, name)
        return res

    def __getitem__(self, name):
        if name in self.variables:
            res = self.variables[name]
        elif name in self.connectors:
            res = self.connectors[name]
        else:
            raise KeyError("No variable or connector named <%s>" % name)
        return res


class ServiceBase(ServiceCommon):
    """
    This class is the base of Real service. No proxy allowed
    """
    exposed_class_name = "Service"

    def setVariableValue(self, vname, value):
        """
        Not very useful, just a dereference of the variable method
        """
        self.variables[vname].value = value

    def getVariableValue(self, vname):
        """
        Again, just getting the value of a variable
        """
        return self.variable[vname].value

    def addConnectorObserver(self, cname, callback, *args):
        """
        Add an observer to a connector. returns an id to the removed callback
        """
        return self.connectors[cname].dispatcher.addObserver(callback, *args)

    def removeConnectorObserver(self, cname, cid):
        """
        Remove an observer from a connector
        """
        self.connectors[cname].removeObserver(cid)

    def connectTo(self, local, proxy, remote):
        """
        This metehod connect to port togheter
        """
        self.connectors[local].connect(getattr(proxy, remote))

    def connectorClientCount(self, cname):
        """
        Returns the number of connected peers
        """
        return self.connectors[cname].peerCount()

    def closeAllConnections(self, cname = None):
        """
        This method close all the connections
        """
        if cname is None:
            for con in self.connectors:
                con.loseConnection()
        else:
            self.connectors[cname].loseConnection()

    def closeConnection(self, cname, peerid):
        """
        This method close a particular connection
        """
        self.connectors[cname].loseConnection(peerid = peerid)





class ProxySupervisor(object):
    """
    This object supervise the access to online attribute of a service proxy.
    Each method which access online attributes should either  : 
        1 - bound the access with a call to acquire/release method
        2 - use a python with statement
    """
    count = 0
    def __init__(self, proxy):
        self.proxy = weakref.ref(proxy)

    def acquire(self):
        """
        This method connect as needed to the remote service and increment the
        service count.
        """
        proxy = self.proxy()
        if not proxy.alive:
            raise RuntimeError("this proxy ain't no more ...")

        self.count += 1
        if self.count == 1:
            proxy.connect()
            if not proxy.resolved:
                proxy.update_description()

    def release(self):
        """
        This method decrement the reference counter and disconnect as needed. To
        ensure we do not reconnect to often. There is a delay between the
        release method call and the real deconnection.
        """
        if self.count == 1:
            reactor.callLater(PROXY_DISCONNECT_TIMEOUT, self.__close__)
        else:
            self.count -= 1

    def __enter__(self):
        self.acquire()

    def __exit__(self, typ, value, traceback):
        self.release()

    def __close__(self):
        if self.count == 1:
            proxy = self.proxy()
            if proxy is not None:
                proxy.disconnect()
        self.count -= 1


class VariableSupervisor(object):
    """
    This object is a Variable Proxy Subscription supervisor. This is intended to
    manage the remote variables subscription. It actually needs a reference to the 
    current connection proxy supervisor.
    """
    count = 0
    def __init__(self, vname, supervisor):
        self.psupervisor = supervisor
        self.vname = vname

    def acquire(self):
        """
        This method nofity that we wants the subscription to remote variable and
        use it.
        """
        self.psupervisor.acquire()
        if self.count == 0:
            proxy = self.psupervisor.proxy()
            proxy.control.query(VARIABLE_SUBSCRIBE % self.vname, proxy.peerid)
        self.count += 0

    def release(self):
        """
        This method notify that we dont need the subscription anymore
        """
        self.count -= 1
        if self.count == 0:
            proxy = self.psupervisor.proxy()
            proxy.query(VARIABLE_UNSUBSCRIBE % self.vname, proxy.peerid)
        self.psupervisor.release()


class ServiceProxy(ServiceCommon):
    """
    This class reprent a remote service and connect as needed to provide remote
    variable changed callback and service introspection.
    """
    resolved = False
    alive = True
    linked = False
    def __init__(self, peerid, host, addr, port, ahost = None):
        """
        Init method
        """
        super(ServiceProxy, self).__init__()
        self.peerid = peerid
        self.host = host
        self.tcp = port
        self.addr = addr
        self.port = port
        self.ahost = ahost
        self.supervisor = ProxySupervisor(self)
        self.vsupervisors = {}

    def __add_variable__(self, name, access_type = None, value = None):
        """
        Internally used to create a VariableProxy inside the serviceproxy
        """
        var = variable.VariableProxy()
        var.name = name
        var.access = access_type
        var.value = value
        self.variables[name] = var
        self.vsupervisors[name] = VariableSupervisor(name, self.supervisor)
        var.valueProxyEvent.addObserver(self.__variable_proxy_changed__, name)

    def __add_connector__(self, name, con_type, tcp = None):
        """
        Internally used method to create a ConnectorProxy inside a serviceproxy
        """
        con = connector.ConnectorProxy(name, self.addr)
        con.tcp = tcp
        con.type = con_type
        con.host = self.host
        self.connectors[name] = con

    def addVariableObserver(self, vname, callback, *args):
        """
        This method add an observer to a remote variable ans subscribe to the
        remote event if needed
        """
        self.vsupervisors[vname].acquire()
        self.control.dispatcher.addProxy(self)
        return ServiceCommon.addVariableObserver(self, vname, callback,
                                                 *args)

    def removeVariableObserver(self, vname, cid):
        """
        This method remove a variable observer and unsubscribe from the remote
        service as needed
        """
        ServiceCommon.removeVariableObserver(self, vname, cid)
        self.control.dispatcher.removeProxy(self)
        self.vsupervisors[vname].release()

    def __build__(self, txt):
        """
        This medhod build a service proxy from a txt record
        """
        if logger.isEnabledFor(logging.INFO):
            logger.info("Building service proxy <%d>" % self.peerid)
        desc = txt.pop(DESCRIPTION_VARIABLE_NAME, None) 
        for key, val in txt.iteritems():
            if len(val) == 1:
                val = val + '/'
            con_type, tcp = val.split('/', 1)
            if con_type in connector.txt_to_connector_type_map:
                self.__add_connector__(key, con_type, tcp = int(tcp))
            else:
                self.__add_variable__(key, con_type, tcp)


        if desc != FULL_DESCRIPTION_VALUE:
            self.update_description()

    def __getattr__(self, attr):
        """
        Ensure we have a good description of the service before letting anyone
        access variables or connector objects.
        """
        if (attr in self.variables) or (attr in self.connectors):
            if not self.resolved:
                self.update_description()
        return ServiceCommon.__getattr__(self, attr)

    def __getitem__(self, name):
        if not self.resolved:
            self.update_description()
        return  ServiceCommon.__getitem__(self, name)


    def update_description(self):
        """
        This method updates the current description for the proxy object. This
        is blocking so dont call it from the mainthread. If it returns, you are
        assured that the description is up to date. Throws an exception if no
        answer.
        """
        with self.supervisor:
            if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Thread blocking function called")
            element = threads.blockingCallFromThread(reactor,
                                                     self.control.query,
                                                     SERVICE_FULL_DESCRIPTION,
                                                     self.peerid)
            self.update(element)

    def connect(self):
        """
        This method connect the proxy to the outside world.
        """
        if self.linked:
            raise RuntimeError("Trying to connect an already connected proxy")
        if logger.isEnabledFor(logging.INFO):
            logger.info("Proxy Connection to the service : %s" 
                        % str(self.peerid))
        self.control.connect(self)
        self.linked = True

    def disconnect(self):
        """
        Force the disconnection of the proxy
        """
        if not self.linked:
            raise RuntimeError("Trying to disconnect an already disconnected proxy")
        if logger.isEnabledFor(logging.INFO):
            logger.info("Proxy Connection close to the service : %s" 
                    % str(self.peerid))
        self.control.disconnect(self.peerid)
        self.linked = False

    def disconnected(self):
        """
        Callback from the control connector.
        """
        self.linked = False

    def update(self, elements):
        """
        This method update the service proxy variables or connector description
        etc.
        """
        self.resolved = True
        for child in elements:
            name = child.attrib['name']
            if not hasattr(self, name):
                if child.tag == VARIABLE_TAG:
                    self.__add_variable__(name)
                else:
                    self.__add_connector__(name, child.tag)
            xml.Marshall.update(ServiceCommon.__getattr__(self, name), child)

    def getVariableValue(self, vname):
        """
        This method query as needed the value of a variable. It should not be
        considered as accurate as the callback since it only ask for the value
        if we dont hava a subscription to the variable.
        """
        var = self.variables[vname]
        if (var.access_type is variable.CONSTANT) and (var.value is not None):
            res = var.__value__
        else:
            with self.supervisor:
                if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Thread blocking function called")
                element = threads.blockingCallFromThread(reactor,
                                                self.control.query,
                                                REQUEST_CONTROL_QUERY % (var.xml_type, vname),
                                                self.peerid)[0]
                res = element.find('value').text
        return res

    def __variable_proxy_changed__(self, value, vname):
            with self.supervisor:
                    self.control.query(VARIABLE_EVENT_MSG % (vname, value), self.peerid)

    def setVariableValue(self, vname, value):
        """
        This method set the remote variable value if the variable is not
        constant
        """
        self.variables[vname].valueProxy = value
            #self.control.query(VARIABLE_EVENT_MSG % (vname, value), self.peerid)

    def getConnectedPeers(self, cname):
        """
        This method returns a list of connected peerid of the given connector 
        name
        """
        conn = self.connectors[cname]
        with self.supervisor:
            if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Thread blocking function called")
            element = threads.blockingCallFromThread(reactor,
                                            self.control.query,
                                            REQUEST_CONTROL_QUERY % (conn.xml_type, cname),
                                            self.peerid)[0]
            el = element.find('peers')
            res = [Peerid(e.text) for e in el.findall('peer')]
        return res



class StartedService(ServiceBase):
    """
    This class represent a service when started. This class cannot be
    instanciate directly or will throw en exception."
    """

    def __init__(self):
        super(StartedService, self).__init__()
        raise Exception("This class cannot be instanciated directly")

    def __stop__(self):
        self.subservices.stopService()
        self.publisher.unpublish()
        self.publisher = None
        self.__class__ = StoppedService

    def stop(self):
        """
        This method stop listening on connectors ports and unpublish the service
        to dnssd
        """
        reactor.callFromThread(self.__stop__)

    def XMLDescription(self):
        """
        Returns a string describing the service.
        """
        vlist = [xml.Marshall.dumps(v) for v in self.variables.itervalues()]
        clist = [xml.Marshall.dumps(c) for c in self.connectors.itervalues()]
        return ''.join(vlist) + ''.join(clist)

    def TXTRecord(self, record = None):
        """
        This is intended to describe the service as a txt record. (a python
        dictionary)
        """
        if record is None:
            record = {}
        for con in self.connectors:
            self.connectors[con].TXTRecord(record = record)
        for var in self.variables:
            self.variables[var].TXTRecord(record = record)
        record['desc'] = 'full'
        return record

    def send(self, cname, msg, peerid = None):
        """
        OMiSCID API, connector redirection
        """
        self.connectors[cname].send(msg, peerid = peerid)

    def sendToAllClients(self, cname, msg):
        """
        OMiSCID API : send message to all connected clients.
        """
        self.connectors[cname].send(msg)

    def sendToOneClient(self, cname, msg, peerid):
        """
        OMiSCID API : send message one particular client on a connector
        """
        self.connectors[cname].send(msg, peerid = peerid)



class StoppedService(ServiceBase):
    """
    This class is a service builder.
    """
    connector_type = { connector.INPUT : connector.IConnector,
                       connector.OUTPUT : connector.OConnector,
                       connector.INOUTPUT : connector.Connector }
    publisher = None

    def __init__(self):
        ServiceBase.__init__(self)
        self.subservices = service.MultiService()
        self.idgen = peerid_generator_factory()
        self.control = connector.ControlConnector()
        self.subservices.addService(self.control)
        self.control.dispatcher.service = weakref.ref(self)
        self.peerid = self.control.peerid = self.idgen.next()

    def addConnector(self, name, description, typ = connector.INOUTPUT):
        """
        This method add a new connector to the service
        """
        if hasattr(self, name) and logger.isEnabledFor(logging.WARNING):
            logger.warning("Name clash detected -- %s --" % name)
        newcon = self.connector_type[typ](description)
        newcon.name = name
        newcon.peerid = self.idgen.next()
        self.connectors[name] = newcon
        self.subservices.addService(newcon)

    def addVariable(self, name, typ, description, access_type =
                    variable.READ_WRITE, value = None):
        """
        This method add a new variable to the service
        """
        if hasattr(self, name) and logger.isEnabledFor(logging.WARNING):
            logger.warning("Name clash detected -- %s --" % name)
        newvar = variable.Variable(typ, description,
                                   access_type, value = value)
        newvar.name = name
        self.variables[name] = newvar

    def __start__(self, domain):
        """
        Must be call in the main thread.
        """
        if not domain.startswith("_bip"):
            raise RuntimeError("domain must begin with _bip")
        self.__class__ = StartedService
        self.subservices.startService()
        self.publisher = BonjourServicePublisher()
        self.publisher.publish(str(self.peerid), self.control.tcp,
                               domain, txt = self.TXTRecord())

    def start(self, domain = OMISCID_DOMAIN):
        """
        This method start the tcp service on the connector and call the dnssd
        publisher to announce the current service.
        """
        reactor.callFromThread(self.__start__, domain)



class ServiceRepository():
    """
    This class is used to dispatch callback of service added and removed from
    the bonjour implementation.
    """
    def __init__(self):
        """
        Init the proxy dict and the observer set.
        """
        self.proxys = {}
        self.observers = {}
        self.uid_gen = generator.uid_generator()

    def dispatchAdded(self, proxy, rtxt):
        """
        This medhod build the service proxy and dispatch the event to the
        observers.
        """
        try:
            proxy.__build__(rtxt)
            self.proxys[proxy.peerid] = proxy 
            for obj, filt, clist, args in self.observers.itervalues():
                try:
                    if (filt is None) or filt(proxy):
                        obj().added(proxy, *args)
                        clist.append(proxy)
                except Exception, err:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.exception(str(err))
        except RuntimeError, err:
            if logger.isEnabledFor(logging.WARNING): 
                logger.warning("Error connecting to remote service ")
                logger.exception(str(err))

    def dispatchRemoved(self, proxy):
        """
        This method dispatch a removed event to the current observers.
        """
        for obj, filt, clist, args in self.observers.itervalues():
            try:
                if proxy in clist: 
                    obj().removed(proxy, *args)
                    clist.remove(proxy)
            except Exception, err:
                if logger.isEnabledFor(logging.WARNING):
                    logger.exception(str(err))

    def added(self, rname, rhost, raddr, rport, rtxt, ahost):
        """
        This is a callback for the BonjourServiceDiscovery. This is called when
        a new service is found.
        """
        peerid = Peerid(str(rname))
        proxy = ServiceProxy(peerid, str(rhost),
                             str(raddr), int(rport), str(ahost))
        reactor.callInThread(self.dispatchAdded, proxy, rtxt)

    def removed(self, rname):
        """
        This is a callback for the BonjourServiceDiscovery. This is called when
        a service is removed from the environment.
        """
        peerid = Peerid(str(rname))
        if peerid in self.proxys:
            proxy = self.proxys[peerid]
            proxy.alive = False
            reactor.callInThread(self.dispatchRemoved, proxy)
            del self.proxys[peerid]

    def addObserver(self, obj, *args, **kw):
        """
        Adding an observer for the serviceAdded and serviceRemoved events.
        """
        filt = kw.pop('filter', None)
        clist = []
        uid = self.uid_gen.next()
        self.observers[uid] = (weakref.ref(obj), filt, clist, args)
        for peerid, proxy in copy.copy(self.proxys).iteritems():
            if (filt is None) or filt(proxy):
                obj.added(proxy, *args)
                clist.append(proxy)
        return uid

    def removeObserver(self, obj):
        """
        Removing an observer.
        """
        del self.observers[obj]

