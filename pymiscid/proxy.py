#
# @Author : Jean-Pascal Mercier <jean-pascal.mercier@gmail.com>
#
# @Copyright (C) 2010 Jean-Pascal Mercier
#
# All rights reserved.
#
#
import new
import weakref

import codebench.events as events

class ConnectorProxyBase(object):
    valid = False
    def __init__(self, connector, cdescription, callback = None):
        self.connector      = connector
        self.valid          = False
        self.oid            = self.connector.addObserver(self)
        self.connector.connect(cdescription)
        self.peerid         = cdescription.peerid
        self.callback       = callback
        self.description    = cdescription

    def connected(self, peerid, evt, description):
        if self.peerid != peerid:
            return

        self.__build__()

    def disconnected(self, peerid):
        if peerid != self.peerid:
            return

        self.valid = False
        self.connector.removeObserver(self.oid)
        self.connector = None

    def __del__(self):
        self.connector.close(peerid = self.peerid)


def RemoteCallWrapper(name):
    def wrapper(self, *args, **kw):
        callback = kw.pop("callback", None)
        return self.connector.call(name, args = args, callback = callback)
    wrapper.__name__ = name
    return wrapper


class RPCConnectorProxy(ConnectorProxyBase):
    def __build__(self):
        self.deferred = None
        cls = type("RPCConnectorProxy_%s" %str(self.peerid), (object,), dict(built = True))
        for name in self.description.methods:
            name = str(name)
            setattr(cls, name, new.instancemethod(RemoteCallWrapper(name), None, cls))

        self.__class__ = cls
        self.valid = True
        if self.callback != None:
            self.callback(self)


class VariableProxy(events.Event):
    last_known_value = None

    def __init__(self, connector, name = None, vtype = None, description = None, value = None):
        events.Event.__init__(self)

        self.name           = name
        self.vtype          = vtype
        self.description    = description
        self.last_value     = value
        self.connector      = weakref.ref(connector)

    def __set_variable_value__(self, value):
        c = self.connector()
        if c is not None:
            c.send("set_variable_value", name, value)

    def __value_changed__(self, value):
        self.last_value = value
        self(value)

    value_changed = property(fset = __value_changed__)

    def __str__(self):
        des = '<VariableProxy name="%s" last_known_value="%s" type="%s" description="%s"' % \
                (self.name, str(self.last_value), str(self.vtype), self.description)
        return des





class VariableConnectorProxy(ConnectorProxyBase):
    def __init__(self, connector, cdescription, callback = None):
        ConnectorProxyBase.__init__(self, connector, cdescription, callback = callback)
        self.connector.register('variable_changed', self.__variable_changed)

    def __build__(self):
        self.deferred = None
        self.methods = {}
        self.variables = {}

        cls = type("RPCConnectorProxy_%s" %str(self.peerid), (object,), dict(built = True))
        for name in self.description.methods:
            name = str(name)
            self.methods[name] = new.instancemethod(RemoteCallWrapper(name), None, cls)
            setattr(cls, name, self.methods[name])

        for vdesc in self.description.variables:
            self.variables[vdesc['name']] = VariableProxy(self, **vdesc)
            setattr(self, vdesc['name'], self.variables[vdesc['name']])

        self.__class__ = cls
        self.valid = True
        if self.callback != None:
            self.callback(self)

    def __variable_changed(self, name, value):
        getattr(self, name).value_changed = value








