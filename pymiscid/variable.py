import codebench.events as events
import weakref

class Variable(object):
    def __init__(self, connector, value = None):
        self.__connector__ = weakref.ref(connector)
        self.__value__ = value

    def __get_value__(self):
        return self.__value__

    def __set_value__(self, value):
        if value != self.__value__:
            self.__value__ = value

    value = property(__get_value__, __set_value__)



class VariableProxy(object):
    def __init__(self, name, peerid, connector):
        self.__connector__ = weakref.ref(connector)
        self.name = name
        self.__peerid__ = peerid

    def __get_value__(self):
        conn = self.__connector__()
        if conn is None:
            raise RuntimeError()

        return conn.send("get_variable_value", self.name,
                         peerid = self.__peerid__, result = True).wait()

    def __set_value__(self, value):
        conn = self.__connector__()
        if conn is None:
            raise RuntimeError()
        if value != conn.send("set_variable_value", self.name, value,
                              peerid = self.__peerid__, result = True).wait():
            raise RuntimeError("Cannot set remote variable")

    value = property(__get_value__, __set_value__)
