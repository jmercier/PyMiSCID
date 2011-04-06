import codebench.events as events

class Variable(events.Event):
    def __init__(self, parser = None, initial = None):
        events.Event.__init__(self)
        self.parser = parser
        self.__value__ = None

    def __get_value__(self):
        return self.__value__ if self.parser is None else self.parser(self.__value__)

    def __set_value__(self, value):
        if self.__value__ != value:
            if self.parser != None:
                self.parser(value)
            self.__value__ = value
            self(value)

    value = property(__get_value__, __set_value__)



