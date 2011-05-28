#!/bin/env python2
#
# @Author : Jean-Pascal Mercier <jean-pascal.mercier@agsis.com>
#
# @Copyright (C) 2010-2011 Jean-Pascal Mercier
#
#
"""
This modules defines de principal constants used during OMiSCID runtime
"""
import os
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
TXT_SEPARATOR               = '/'

OUTPUT_CONNECTOR_PREFIX     = 'o'
INPUT_CONNECTOR_PREFIX      = 'i'
IO_CONNECTOR_PREFIX         = 'd'

CONSTANT_PREFIX             = 'c'
WRITE_VARIABLE_PREFIX       = 'w'
READ_VARIABLE_PREFIX        = 'r'


DESCRIPTION_VARIABLE_NAME   = 'desc'
FULL_DESCRIPTION_VALUE      = 'full'
PART_DESCRIPTION_VALUE      = 'part'
PREFIX_LEN = 2

#
# General
#
UNBOUNDED_PEERID            = 0xFFFFFF00
UNBOUNDED_SERVICE_NAME      = "unbound service"
UNBOUNDED_CONNECTOR_NAME    = "unbound connector"
UNBOUNDED_VARIABLE_NAME     = "unbound variable"

QUERY_TIMEOUT               = 5 #seconds
CONNECTION_TIMEOUT          = 5 #seconds
PROXY_DISCONNECT_TIMEOUT    = 5 #seconds
