import json
import codebench.wref as wref
import weakref

import codebench.events as events

import connector

import threading
import variable

class TimeoutError(Exception): pass


def id_generator(init = 0):
    while True:
        yield init
        init += 1


class DeferredResult(events.Event):
    def __init__(self, rid, connector):
        events.Event.__init__(self)

        self.__recv_evt__ = threading.Event()
        self.__results__ = []
        self.rid = rid
        self.wconnector = weakref.ref(connector)

    def __set_result__(self, result):
        self(result)

        self.__results__.append(result)
        self.__recv_evt__.set()
        self.__recv_evt__ = threading.Event()

    def addObserver(self, observer, *args, **kw):
        events.Event.addObserver(self, observer, *args, **kw)
        for r in self.__results__:
            self(r)


    result = property(fset = __set_result__)


    def wait(self, timeout = 10):
        if len(self.__results__) < 1:
            if not self.__recv_evt__.wait(timeout = timeout):
                raise TimeoutError("Deferred Result Timeout Reached")

        res = self.__results__.pop()
        if isinstance(res, Exception):
            raise res

        return res


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
    __rpcid__ = id_generator()
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
                                    jsondict['id'], peerid)

    def bind(self, obj):
        """
        """
        for name in dir(obj):
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "__remote_callable__"):
                self.register(name, attr)

        self.__bounded__.append(obj)

    def __process_rpc__(self, method, params, cid, peerid):
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

    def send(self, method, *args, **kw):
        """
        :param id: message id
        """
        rneeded = kw.pop("result", False)
        rpcid = self.__rpcid__.next() if rneeded else None
        msg = json.dumps({"method" : method,
                           "params" : args,
                           "id" : rpcid})

        result = None
        if rpcid is not None:
            result = DeferredResult(rpcid, self)
            self.__pending_results__[rpcid] = weakref.ref(result)
        connector.ConnectorBase.send(self, msg)

        return result

def remote_callable(fct):
    setattr(fct, "__remote_callable__", True)
    return fct

class VariableConnector(RPCConnector):
    def __init__(self):
        RPCConnector.__init__(self)
        self.__remote_variables__ = {}
        self.__local_variables__ = {}
        self.bind(self);
        self.__list_results__ = {}

    def start(self, *args, **kw):
        RPCConnector.start(self, *args, **kw)

    def connected(self, proto, rpeerid):
        RPCConnector.connected(self, proto, rpeerid)
        res = self.send("get_variable_list", result = True)
        self.__list_results__[rpeerid] = res

        res.addObserver(self.__received_variable_list__, rpeerid)

    def __received_variable_list__(self, varlist, rpeerid):
        proxydict = {}
        for v in varlist:
            proxydict[v] = variable.VariableProxy(v, rpeerid, self)
        self.__remote_variables__[rpeerid] = proxydict
        del self.__list_results__[rpeerid]

    def disconnected(self, proto, rpeerid):
        RPCConnector.disconnected(self, proto, rpeerid)
        if rpeerid in self.__remote_variables__:
            del self.__remote_variables__[rpeerid]


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

if __name__ == '__main__':
    import variable
    vc = VariableConnector()
    v = variable.Variable(vc, 2)
    vc.__local_variables__['test'] = v
    vc.start()
    print vc.tcp
    import reactor
    reactor.Reactor().run()
    vc.close()


