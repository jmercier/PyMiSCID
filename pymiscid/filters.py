# vim: ts=4 sw=4 sts=0 expandtab:
"""
This module contain different easy to use proxy filter
"""

class HasVariable(object):
    """
    This filter verify the existance of a variable and optionally the value of
    this variable.
    """
    value = None
    def __init__(self, vname, value = None):
        self.vname = vname
        if value is not None:
            self.value = str(value)

    def __call__(self, proxy, *args, **kw):
        res = False
        if self.vname in proxy.variables:
            res = (self.value is None) or \
                  (proxy.getVariableValue(self.vname) == self.value)
        return res

class NameIs(object):
    """
    This filter verify the name of the service
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, proxy, *args, **kw):
        return proxy.getVariableValue("name") == self.name

class HostPrefixIs(object):
    """
    This filter verify that the prefix of the host of the service starts with
    the given prefix
    """
    def __init__(self, host):
        self.host = host

    def __call__(self, proxy, *args, **kw):
        return proxy.host.startswith(self.host)

class HasConnector(object):
    """
    This filter verify the existance of a connector
    """
    def __init__(self, cname):
        self.cname = cname

    def __call__(self, proxy, *args, **kw):
        return self.cname in proxy.connectors

class Not(object):
    """
    This filter implement the logic operator Not
    """
    def __init__(self, filt):
        self.filter = filt

    def __call__(self, proxy, *args, **kw):
        return not self.filter(proxy)

class Or(object):
    """
    This filter implement the logic operator Or. This can be used with an
    arbitrary number of other filters.
    """
    def __init__(self, *args):
        self.filters = args

    def __call__(self, proxy, *args, **kw):
        for f in self.filters:
            if f(proxy):
                return True

class And(object):
    """
    This filter implement the logic operator and...
    """
    def __init__(self, *args):
        self.filters = args
    
    def __call__(self, proxy, *args, **kw):
        res = True
        for f in self.filters:
            if not res:
                break
            res = f(proxy)
        return res

class PeeridIs(object):
    """
    This filter works on the peerid of the service. It always use the base of
    the given peerid so it is possible to use connector peerid in this filter.
    """
    def __init__(self, peerid):
        self.peerid = peerid.base()
        print str(self.peerid)

    def __call__(self, proxy, *args, **kw):
        print proxy, args, kw
        return self.peerid == proxy.peerid

