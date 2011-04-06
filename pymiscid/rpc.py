import json
import codebench.wref as wref
import weakref

import connector

import threading

class DeferredResult(object):
    def __init__(self, rid, connector):
        self.__recv_evt__ = threading.Event()
        self.__results__ = []
        self.rid = rid
        self.wconnector = weakref.ref(connector)

    def __set_result__(self, result):
        self.__results__.append(result)
        self.__recv_evt__.set()
        self.__recv_evt__ = threading.Event()


    result = property(fset = __set_result__)


    def __call__(self, timeout = 10):
        if len(self.__results__) < 1:
            if not self.__recv_evt__.wait(timeout = timeout):
                raise TimeoutError("Deferred Result Timeout Reached")

        res = self.__results__.pop()
        if isinstance(res, Exception):
            raise res

        return res

    wait = __call__

    def __del__(self):
        connector = self.wconnector()
        if connector is None:
            return

        if self.rid in connector.__pending_results__:
            del connector.__pending_results__[self.rid]

class StructuredConnector(connector.Connector):
    def send(self, structured_msg):
        connector.Connector.send(json.dumps(structured_msg))

    def received(self, proto, peerid, msgid, msg):
        """
        Callback override from BIP protocol when message is received

        :param proto: The actual protocol object where the event occured
        :param msg: The string message

        """
        protocol.BIPFactory.received(self, proto, peerid, msgid, msg)
        self.receivedEvent(msg)


class RPCConnector(connector.ConnectorBase):
    def __init__(self, peerid = None):
        connector.ConnectorBase.__init__(self, peerid = peerid)

        self.__rcallables__ = {}
        self.__bounded__ = []
        self.__pending_results__ = {}

        self.register("listing", self.__listing__)

    def register(self, name, method):
        self.__rcallables__[name] = wref.WeakBoundMethod(method)

    def __deferred_deleted__(self, deferred):
        pass

    def received(self, proto, peerid, msgid, msg):
        """
        """

        connector.ConnectorBase.received(self, proto, peerid, msgid, msg)
        if len(msg) == 0:
            return

        jsondict = json.loads(msg)
        if "result" in jsondict:
            self.__process_result__(jsondict['result'], jsondict['error'],
                                 jsondict['id'])
        else:
            self.__process_rpc__(jsondict['method'], jsondict['params'],
                                    jsondict['id'])


    def bind(self, obj):
        """
        """
        for name in dir(obj):
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "__remote_callable__"):
                self.register(name, attr)

        self.__bounded__.append(obj)



    def __process_rpc__(self, method, params, cid):
        resultdict = {"error" : None, "result" : None, "id" : cid}
        try:
            fct = self.__rcallables__[method]()
            if fct is None:
                del self.__rcallables__[method]
            else:
                resultdict['result'] = self.__rcallables__[method]()(*params)
        except Exception, e:
            resultdict['error'] = [e.__class__.__name__, str(e)]
            #import traceback
            #traceback.print_exc()

        if cid != None:
            connector.ConnectorBase.send(self, json.dumps(resultdict))


    def __listing__(self):
        """
        """
        return self.__rcallables__.keys()


    def __process_result__(self, result, error, cid):
        if cid in self.__pending_results__:
            deferred = self.__pending_results__[cid]()
            if deferred is None:
                return

            if error is None:
                deferred.result = result
            else:
                deferred.result = Exception(error)

        else:
            # Should log something
            pass

    def send(self, method, *args, **kw):
        """
        :param id: message id
        """
        rpcid = kw.pop("id", None)
        msg = json.dumps({"method" : method,
                           "params" : args,
                           "id" : rpcid})

        result = None
        if rpcid is not None:
            result = DeferredResult(rpcid, self)
            self.__pending_results__[rpcid] = weakref.ref(result)
        connector.ConnectorBase.send(self, msg)

        return result


class TimeoutError(Exception): pass





class RPCDispatcher(object):
    def __init__(self):
        self.__rcallables__ = {}
        self.__bounded__ = []
        self.__deferred__ = {}


    def bind(self, obj):
        for name in dir(obj):
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "__remote_callable__"):
                self.register(name, attr)

        self.register("__list__", self.__list__)
        self.__bounded__.append(obj)

    def __list__(self):
        print self.__rcallables__.keys()
        return self.__rcallables__.keys()

    def connectedEvent(self, rpeerid):
        print "Client Connected"

    def disconnectedEvent(self, rpeerid):
        print "Client Disconnected"

    def register(self, name, method):
        print "Registering : " + name
        self.__rcallables__[name] = wref.WeakBoundMethod(method)

    def __process_rpc__(self, method, params, cid):
        resultdict = {}
        if method in self.__rcallables__:
            try:
                fct = self.__rcallables__[method]()
                if fct is None:
                    del self.__rcallables__[method]
                else:
                    resultdict['result'] = self.__rcallables__[method]()(*params)
            except Exception, e:
                import traceback
                traceback.print_exc()
        else:
            resultdict['error'] = [1, 'asdfa']

        return resultdict


    def __process_result__(self, result, error, cid):
        if cid in self.__deferred__:
            if error is not None:
                self.deferred[cid].result = Exception(error)
            else:
                self.deffered[cid].result = result
        else:
            # Should log something
            pass


    def receivedEvent(self, msg):
        jsondict = json.loads(msg)
        if "result" in jsondict:
            self.__process_rpc__(jsondict['result'], jsondict['error'],
                                 jsondict['id'])
        else:
            self.__process_result__(jsondict['method'], jsondict['params'],
                                    jsondict['id'])


class RPCConverter(object):
    def __call__(self, method, *args, **kw):
        rpcid = kw.pop("id", None)
        return json.dumps({"method" : method,
                           "params" : args,
                           "id" : rpcid})

def remote_callable(fct):
    setattr(fct, "__remote_callable__", True)
    return fct


class test(object):
    @remote_callable
    def method1(self, *args):
        print args

class ObjectProxy(object):
    def bind(self, connector):
        self.connector = connector
        self.__remote_callable__ = {}

    def connected(self, *args):
        print "Connected"

    def disconnected(self, *args):
        print "DisConnected"

    def received(self, *args):
        print "euh"

    def call(self, method, *args):
        self.connector.send(method, *args, id = 1)


