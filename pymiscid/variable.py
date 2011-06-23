import codebench.events as events

class Variable(events.Event):
    def __init__(self, vtype, description, value = None):
        events.Event.__init__(self)

        self.vtype              = vtype
        self.description        = description
        self.__value            = value

    def __set_variable_value(self, value):
        if (value == self.__value):
            return

        self.__value = value
        self(value)

    def __get_variable_value(self):
        return self.__value

    value = property(__get_variable_value, __set_variable_value)


