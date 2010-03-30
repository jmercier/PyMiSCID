#
#
#
import logging

from lxml import etree
from lxml import objectify

logger = logging.getLogger(__name__)

def dictify(el):
    d = {};
    d.update(el.attrib)
    for k, l in el.__dict__.iteritems():
        d[k] = [dictify(e) for e in l]
    return d

def build_element(root, cval):
    """
    This method build the element depending on the type of the value
    """
    if hasattr(cval, '__iter__'):
        for sval in cval:
            c = etree.Element(root.tag[:-1])
            c.text = str(sval)
            root.append(c)
    else:
        root.text = None if cval is None else str(cval)


class Marshall(object):
    """
    Simple marchaling and updating class

    xml_tag
    xml_childs
    xml_attributes
    xml_updatable
    xml_value
    """
    @staticmethod
    def dump(obj):
        element = etree.Element(obj.xml_tag)
        try:
            for a in obj.xml_attributes:
                element.attrib[a] = str(getattr(obj, a))
        except AttributeError, err:
            pass
        try:
            for ctag in obj.xml_childs:
                ce = etree.Element(ctag)
                cval = getattr(obj, ctag)
                build_element(ce, cval)
                element.append(ce)
        except AttributeError, err:
            pass
        return element

    @staticmethod
    def dumps(obj):
        return etree.tostring(Marshall.dump(obj))


    @staticmethod
    def update(obj, xmlobj):
        for xo in xmlobj.getchildren():
            if xo.tag in obj.xml_updatable:
                val = '' if xo.text is None else xo.text
                setattr(obj, xo.tag, val)
            else:
                if logger.isEnabledFor(logging.WARNING): 
                    logger.warning("Trying to update an unupdatable attribute -- %s -- " % xo.tag)




