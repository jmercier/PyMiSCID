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
    def send(self, structured_msg, *args, **kw):
        connector.Connector.send(json.dumps(structured_msg, *args, **kw))

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


class TheConnector(connector.Connector):
    def send(self, structured_message, **kw):
        connector.Connector

class RPCConnector(connector.Connector):
    events          = ['connected', 'disconnected']
    structure       = "JSON"
    ctype           = "RPC"
    __rpcid__       = id_generator()
    def __init__(self, *args, **kw):
        connector.Connector.__init__(self, *args, **kw)

        self.__rcallables__ = {}
        self.__pending_results__ = {}


    def register(self, name, method):
        wmethod = wref.WeakBoundMethod(method) if isinstance(method, new.instancemethod) else weakref.ref(method)
        self.__rcallables__[name] = wmethod


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

    def __process_rpc__(self, method, params, cid, peerid):
        resultdict = {"error" : None, "result" : None, "id" : cid}
        try:
            fct = self.__rcallables__[method]()
            if fct is None:
                del self.__rcallables__[method]
            else:
                resultdict['result'] = fct(*params)
        except Exception as e:
            import traceback
            traceback.print_exc()
            resultdict['error'] = [e.__class__.__name__, str(e)]

        if cid != None:
            connector.ConnectorBase.send(self, json.dumps(resultdict), peerid = peerid)

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

        result = None
        if callback is not None:
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
        self.variables      = {}

        self.register("set_variable_value", self.set_variable_value)
        self.register("get_variable_value", self.get_variable_value)

    def add_variable(self, vname, v):
        v.addObserver(self.variable_changed, vname)
        self.variables[vname] = v

    def variable_changed(self, value, vname):
        self.send("variable_changed", (vname, value))

    def set_variable_value(self, variable, value):
        var = self.__local_variables[variable]
        var.value = value
        return var.value

    def get_variable_value(self, variable):
        return self.__local_variables[variable].value







