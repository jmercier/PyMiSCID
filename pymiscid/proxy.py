import new

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


class VariableConnectorProxy(ConnectorProxyBase):
    def __connected__(self):
        self.deferred = self.connector.call("get_variable_list",
                                            peerid = self.peerid,
                                            callback = self.__build__)

    def __build__(self, variables):
        print(variables)


