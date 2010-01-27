#
"""
This modules defines de principal constants used during OMiSCID runtime
"""
import os
import xsd
import logging

logger = logging.getLogger(__name__)

OMISCID_DOMAIN = os.environ.get("OMISCID_WORKING_DOMAIN", "_bip._tcp")
if not OMISCID_DOMAIN.startswith("_bip"):
    if logger.isEnabledFor(logging.WARNING):
        logger.warning("OMiSCID Domain must begin with a _bip")
    OMISCID_DOMAIN = "_bip._tcp"
#
# TXT Record
#
CONSTANT_PREFIX = 'c'
READ_PREFIX = 'r'
READ_WRITE_PREFIX = 'w'


TXT_SEPARATOR = '/'

OUTPUT_CONNECTOR_PREFIX = 'o'
INPUT_CONNECTOR_PREFIX = 'i'
IO_CONNECTOR_PREFIX = 'd'

WRITE_VARIABLE_PREFIX = 'w'
READ_VARIABLE_PREFIX = 'r'

XML_IO_CONNECTOR_TAG = 'inoutput'
XML_I_CONNECTOR_TAG = 'input'
XML_O_CONNECTOR_TAG = 'output'

XML_CONSTANT_TAG = 'constant'
XML_READ_TAG = 'read'
XML_READ_WRITE_TAG = 'readWrite'


DESCRIPTION_VARIABLE_NAME = 'desc'
FULL_DESCRIPTION_VALUE = 'full'
PREFIX_LEN = 2

#
# Control Protocol
#
CONTROL_QUERY = '<?xml version="1.0" standalone="yes"?><controlQuery id="%08.x">%s</controlQuery>'
CONTROL_EVENT = '<?xml version="1.0" standalone="yes"?><controlEvent>%s</controlEvent>'
CONTROL_ANSWER = '<?xml version="1.0" standalone="yes"?><controlAnswer id="%08.x">%s</controlAnswer>'
CONTROL_QUERY_TAG = 'controlQuery'
CONTROL_EVENT_TAG = 'controlEvent'
CONTROL_ANSWER_TAG = 'controlAnswer'

#
# Control MSG
#
REQUEST_CONTROL_QUERY = '<%s name="%s"/>'
VARIABLE_EVENT_MSG = '<variable name="%s"><value><![CDATA[%s]]></value></variable>'
VARIABLE_SUBSCRIBE = '<subscribe name="%s"/>'
VARIABLE_UNSUBSCRIBE = '<unsubscribe name="%s"/>'
XML_VARIABLE_TYPE = 'variable'

SERVICE_FULL_DESCRIPTION = '<fullDescription/>'


#
# XSD
#a
CONTROL_ANSWER_XSD = xsd.control_answer
CONTROL_QUERY_XSD = xsd.control_query
SERVICE_XSD = xsd.service


# General
#
UNBOUNDED_SERVICE_NAME = "unbound service"
UNBOUNDED_CONNECTOR_NAME = "unbound connector"
UNBOUNDED_VARIABLE_NAME = "unbound variable"
PEERID = "%08.x" 
QUERY_TIMEOUT = 5 #seconds
CONNECTION_TIMEOUT = 5 #seconds
PROXY_DISCONNECT_TIMEOUT = 5

OUTPUT_CONNECTOR_TYPE = OUTPUT_CONNECTOR_PREFIX[0]
INPUT_CONNECTOR_TYPE = INPUT_CONNECTOR_PREFIX[0]
IO_CONNECTOR_TYPE = IO_CONNECTOR_PREFIX[0]

#
# Variables
#
LOCK_DESCRIPTION = "LOCK DESCRIPTION"
LOCK_TYPE = "bool"


#
# QUERY tags
#
VARIABLE_TAG = 'variable'
FULLDESC_TAG  = 'fullDescription'
SUBSCRIBE_TAG  = 'subscribe'
UNSUBSCRIBE_TAG = 'unsubscribe'
INPUT_CONNECTOR_TAG = 'input'
OUTPUT_CONNECTOR_TAG = 'output'
IO_CONNECTOR_TAG = 'inoutput'
