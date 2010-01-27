#
"""
This module contains the class representin OMiSCID variables.
"""
import logging

from codebench.events import ThreadsafeEvent

from cstes import CONSTANT_PREFIX, \
                  READ_PREFIX, \
                  READ_WRITE_PREFIX, \
                  TXT_SEPARATOR, \
                  XML_VARIABLE_TYPE, \
                  XML_CONSTANT_TAG, \
                  XML_READ_TAG, \
                  XML_READ_WRITE_TAG

logger = logging.getLogger(__name__)

CONSTANT, READ, READ_WRITE = range(3)

access_type_to_txt_dict = { CONSTANT : CONSTANT_PREFIX,
                            READ : READ_PREFIX,
                            READ_WRITE : READ_WRITE_PREFIX }
txt_dict_to_access_type = { CONSTANT_PREFIX : CONSTANT ,
                            READ_PREFIX : READ ,
                            READ_WRITE_PREFIX : READ_WRITE}

access_type_to_xml_dict = { CONSTANT : XML_CONSTANT_TAG,
                            READ : XML_READ_TAG,
                            READ_WRITE : XML_READ_WRITE_TAG }
xml_to_access_type_dict = { XML_CONSTANT_TAG : CONSTANT,
                            XML_READ_TAG : READ,
                            XML_READ_WRITE_TAG : READ_WRITE }

class VariableBase(ThreadsafeEvent):
    """
    This class represent the common base for both variable proxy and local
    variables.
    """
    type = ''
    xml_type = XML_VARIABLE_TYPE
    access_type = READ_WRITE
    description = ''
    __value__ = None
    name = 'Unbounded'

    def __get_access__(self):
        return access_type_to_xml_dict[self.access_type]
    access = property(__get_access__)

    def __get_value__(self):
        """
        Get the variable value
        """
        return self.__value__

    def __set_value__(self, val):
        """
        Set the variable value and call the observers callback.
        """
        if val != self.__value__:
            self.__value__ = val
            self(val)
    value = property(__get_value__, __set_value__)


class VariableProxy(VariableBase):
    """
    This class represent a remote variable. Not much to add bot except that we
    can set the access of a remote variable proxy.
    """
    xml_updatable = ['description', 'access',
                     'type', 'formatDescription', 'value']

    def __set_access__(self, value):
        if value in txt_dict_to_access_type:
            self.access_type = txt_dict_to_access_type[value]
        elif value in xml_to_access_type_dict:
            self.access_type = xml_to_access_type_dict[value]
        else:
            self.access_type = value
    access = property(VariableBase.__get_access__, __set_access__)


class Variable(VariableBase):
    """
    This class represent a local variable. It implement a validator which permit
    to validate a value before the value is really setted.
    """
    validator = None
    xml_tag = 'variable'
    xml_attributes = ['name']
    xml_childs = ['description', 'type', 'value', 'access']

    def __init__(self, typ, description, access_type, value = ''):
        VariableBase.__init__(self)
        self.type = typ
        self.__value__ = str(value)
        self.access_type = access_type
        if (self.access_type is CONSTANT) and (value is None):
            raise RuntimeError("You must specify constant value at init time")
        self.description = description
        self.xml_updatable = ['value'] if self.access_type is READ_WRITE else []

    def TXTRecord(self, record = None):
        """
        This method appends the current txt to the given record and returns 
        the record.
        """
        if record is None:
            record = {}
        if self.access_type is CONSTANT:
            record[self.name] = \
                        ''.join([CONSTANT_PREFIX, TXT_SEPARATOR, self.value])
        else:
            record[self.name] = access_type_to_txt_dict[self.access_type]
        return record

    def set_validator(self, callback, *args, **kw):
        """
        This method add a validator callback to validate the value of the
        variable.
        """
        self.validator = [callback, args, kw]

    def unset_validator(self):
        """
        This method remove the validator from the variable object.
        """
        self.validator = None

    def __set_value__(self, val):
        """
        Set the variable value and call the observers callback.
        """
        if self.access_type is CONSTANT:
            raise RuntimeError("Cannot set value of a constant variable")

        if val != self.__value__:
            if (self.validator is None) or self.validator[0](self.value,
                                    *self.validator[1], **self.validator[2]):
                self(val)





