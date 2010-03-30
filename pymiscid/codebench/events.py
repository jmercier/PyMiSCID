#
#
# vim: ts=4 sw=4 sts=0 expandtab:
from __future__ import with_statement
import os, new, copy, weakref, threading, time
import logging
import wref

import generator

logger = logging.getLogger(__name__)


class EventSupervisor(object):
        processing = False
        triggered = 0
        def __init__(self):
            self.creation_time = time.time()

        def __enter__(self):
            self.processing = True
            self.triggered += 1

        def __exit__(self, typ, value, traceback):
            self.processing = False


class Event(object):
    """
    This is a simple object which represent an event it can be dispatched which
    notifies every observer of this event.  WARNING : The default behavior only 
    keeps weakref so KEEP REFERENCE.
    """
    name = ""
    def __init__(self, **kw):
        """
        Init procedure
        """
        self.observers = {}
        self.supervisor = EventSupervisor()
        self.uid_gen = generator.uid_generator()
        self.wref = kw.pop("weakref", True)

    def addObserver(self, observer, *args, **kwarg):
        """
        This method add an observer for this event. Every argument passed to
        this function will be forwarded to the callback when the event is fired
        """
        if not callable(observer):
            raise RuntimeError("Observer must be callable")

        oid = self.uid_gen.next() if "oid" not in kwarg else kwarg.pop("oid")
        if oid in self.observers:
            if logger.isEnabledFor(logger.WARNING):
                logger.warning("Observer ID collision detected [%s]" % str(oid))

        obj = observer
        if self.wref:
            obj = wref.WeakBoundMethod(obj) if isinstance(obj,new.instancemethod) else weakref.ref(obj)

        self.observers[oid] = (obj, args)
        return oid

    def removeObserver(self, oid):
        """
        This method remove an observer for the event.
        """
        del self.observers[oid]

    def dispatch(self, *args):
        """
        This method dispatch the events with arguments which are forwarded to
        the listener functions.
        """
        o2 = copy.copy(self.observers)
        with self.supervisor:
            for oid, (callback, cargs) in o2.iteritems():
                try:
                    if self.wref:
                        callback = callback()

                        if callback is not None:
                            callback(*(args + cargs))
                        else:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug("Observer event deleted id [%d]" % oid)
                            del self.observers[oid]
                    else:
                        callback(*(args + cargs))
                except Exception, e:
                    logger.exception(str(e))

    __call__ = dispatch

    def clear(self):
        """
        Clear the observer dictionary.
        """
        self.observers = {}

    def __len__(self):
        return len(self.observers)




class EventDispatcherBase(object):
    """
    This object act as a base object for an aglomerate of events. It provides
    the possibility tp register a single object for every events in the object.
    It is also in charge of initializing events.
    """
    events = []
    event_type = Event
    def __init__(self, **kw):
        """
        Simple Init method which creates the events
        """
        self.uid_gen = generator.uid_generator()
        for evt_name in self.events:
            if hasattr(self, evt_name + "Event"):
                    logger.warning("Event Function Override -- %s --" % evt_name)
            else:
                evt = self.event_type(**kw)
                setattr(self, evt_name + "Event", evt)
                evt.name = evt_name

    def addObserver(self, obj, *args,  **kw):
        """
        Add the right method observer to the contained event
        """
        oid = self.uid_gen.next() if "oid" not in kw else kw.pop("oid")
        for evt in self.events:
            try:
                getattr(self, evt + "Event").addObserver(getattr(obj, evt), *args, oid = oid)
            except AttributeError, err:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("Object : %s do not have attribute -- %s --" % \
                               (repr(obj), evt))
        return oid

    def removeObserver(self, oid):
        """
        Remove the right method observer to the contained event
        """
        for evt in self.events:
            try:
                getattr(self, evt + "Event").removeObserver(oid)
            except AttributeError, err:
                pass

    def clear(self):
        """
        Clear all events of this object
        """
        for evt in self.eents:
            getattr(self, evt + "Event").clear()

    def dispatch(self, evtname, *args):
        if evtname in self.events:
            getattr(self, evtname + "Event")(*args)


class MutexedEvent(Event):
        def __init__(self, mutex = None):
                Event.__init__(self)
                self.mutex = threading.Lock() if mutex is None else mutex

        def dispatch(self, *args):
                with self.mutex:
                        Event.dispatch(self, *args)


class MutexedEventDispatcher(EventDispatcherBase):
        event_type = MutexedEvent
        def __init__(self, *args, **kw):
            """
            Simple Init method which creates the events
            """
            self.mutex = threading.Lock()
            if "mutex" not in kw:
                kw["mutex"] = self.mutex
            EventDispatcherBase.__init__(self, *args, **kw)


