from __future__ import print_function

import json
import codebench.wref as wref
import weakref

import codebench.events as events

import connector

import threading
import variable
import new

class TimeoutError(Exception): pass


def id_generator(init = 0):
    while True:
        yield init
        init += 1

class MethodCallback(object):
    def __init__(self, fct, *args):
        self.fct    = fct
        self.args   = args

    def __call__(self, *args):
        self.fct(*(args + self.args))


class DeferredCallback(object):
    def __init__(self, rid, connector, callback, args):
        self.rid            = rid
        self.wconnector     = weakref.ref(connector)
        self.callback       = callback
        self.args           = args

    def __set_result__(self, result):
        self.callback(result, *self.args)

    result = property(fset = __set_result__)

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
        connector.ConnectorBase.received(self, proto, peerid, msgid, msg)
        if len(msg) == 0:
            return

        jsondict = json.loads(msg)
        self.receivedEvent(jsondict)



class ConnectorProxyBase(object):
    valid = False
    def __init__(self, connector, cdescription, callback = None):
        self.connector  = connector
        self.valid      = False
        self.oid        = self.connector.addObserver(self)
        self.connector.connect(cdescription)
        self.peerid     = cdescription.peerid
        self.callback   = callback

    def connected(self, peerid):
        if self.peerid == peerid:
            self.__connected__()

    def __connected__(self):
        pass

    def disconnected(self, peerid):
        if peerid == self.peerid:
            self.valid = False
        self.connector.removeObserver(self.oid)
        self.connector = None

    def __del__(self):
        self.connector.close(peerid = self.peerid)


class RPCConnectorProxy(ConnectorProxyBase):
    def __connected__(self):
        self.deferred = self.connector.call("__listing",
                                            peerid = self.peerid,
                                            callback = self.__build__)

    def __build__(self, description):
        self.deferred = None
        fcts = {}
        cls = type("RPCConnectorProxy_%s" %str(self.peerid), (object,), dict(built = True))
        for fct in description:
            def fct_proxy(self, *args, **kw):
                if "callback" not in kw:
                    self.connector.send(fct, args = args)
                else:
                    return self.connector.call(fct, args = args, callback = kw['callback'])
            fct_proxy.__name__ = str(fct)
            setattr(cls, fct, new.instancemethod(fct_proxy, None, cls))

        self.__class__ = cls
        self.valid = True
        if self.callback != None:
            self.callback(self)



class RPCConnector(connector.Connector):
    events          = ['connected', 'disconnected']
    structure       = "JSON RPC"
    __rpcid__       = id_generator()
    def __init__(self, *args, **kw):
        connector.Connector.__init__(self, *args, **kw)

        self.__rcallables__ = {}
        self.__bounded__ = []
        self.__pending_results__ = {}

        self.register("__listing", self.__listing)



    def register(self, name, method):
        wmethod = wref.WeakBoundMethod(method) if isinstance(method, new.instancemethod) else weakref.ref(method)
        self.__rcallables__[name] = wmethod

    def __deferred_deleted__(self, deferred):
        pass

    def received(self, proto, peerid, msgid, msg):
        """
        """

        connector.ConnectorBase.received(self, proto, peerid, msgid, msg)
        if msgid == 0:
            return

        jsondict = json.loads(msg)
        if "result" in jsondict:
            self.__process_result__(jsondict['result'], jsondict['error'],
                                 jsondict['id'])
        else:
            self.__process_rpc__(jsondict['method'], jsondict['params'],
                                    jsondict['id'], peerid)

    def bind(self, obj):
        """
        """
        for name in dir(obj):
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "__remote_callable__"):
                self.register(name, attr)

        self.__bounded__.append(obj)
        self.addObserver(obj)

    def __process_rpc__(self, method, params, cid, peerid):
        resultdict = {"error" : None, "result" : None, "id" : cid}
        try:
            fct = self.__rcallables__[method]()
            if fct is None:
                del self.__rcallables__[method]
            else:
                resultdict['result'] = self.__rcallables__[method]()(*params)
        except Exception as e:
            resultdict['error'] = [e.__class__.__name__, str(e)]

        if cid != None:
            connector.ConnectorBase.send(self, json.dumps(resultdict), peerid = peerid)

    def __listing(self):
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

    def send(self, method, args = (), peerid = None):
        """
        :param id: message id
        """
        msg = json.dumps({"method" : method,
                           "params" : args,
                           "id" : None})

        connector.ConnectorBase.send(self, msg, peerid = peerid)


    def call(self, method, args = (), peerid = None, callback = None):
        """
        :param id: message id
        """
        rpcid       = self.__rpcid__.next()
        msg         = json.dumps({"method" : method,
                                  "params" : args,
                                  "id" : rpcid})

        result = DeferredCallback(rpcid, self, callback, ())

        self.__pending_results__[rpcid] = weakref.ref(result)
        connector.ConnectorBase.send(self, msg, peerid = peerid)

        return result






def remote_callable(fct):
    setattr(fct, "__remote_callable__", True)
    return fct

class VariableConnector(RPCConnector):
    def __init__(self):
        RPCConnector.__init__(self)
        self.__local_variables      = {}
        self.__list_results         = {}

        self.bind(self);

    @remote_callable
    def set_variable_value(self, variable, value):
        var = self.__local_variables__[variable]
        var.value = value
        return var.value

    @remote_callable
    def get_variable_value(self, variable):
        return self.__local_variables__[variable].value

    @remote_callable
    def get_variable_list(self):
        return self.__local_variables__.keys()


class VariableConnectorProxy(ConnectorProxyBase):
    def __connected__(self):
        self.deferred = self.connector.call("get_variable_list",
                                            peerid = self.peerid,
                                            callback = self.__build__)

    def __build__(self, variables):
        print(variables)



