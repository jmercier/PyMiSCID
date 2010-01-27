"""
This module parse the xsd files for OMiSCID validation purposes.
"""
import os
import sys
import logging

from lxml import etree

__module__ = sys.modules[__name__]
logger = logging.getLogger(__name__)


xsd_files = { 'control_query' : 'control-query.xsd',
              'control_answer' : 'control-answer.xsd',
              'service' : 'service.xsd' }

for name, filename in xsd_files.iteritems():
    path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(path):
        element = etree.parse(os.path.join(os.path.dirname(__file__), filename))
        setattr(__module__, name, element)
    else:
        name = None
        logger.warning("Cannot find xsd file -- %s -- " % filename)

