import weakref
import new

class WeakBoundMethod(object):
        """
        This class is intended to represent a weakref to a bound
        method. This make it happen by keeping a ref to the function and the class
        then a weakref to the object itself.
        """
        def __init__(self, method):
                """
                Init method
                """
                self.im_func = method.im_func
                self.im_self = weakref.ref(method.im_self)
                self.im_class = method.im_class

        def __call__(self, *args, **kw):
                """
                This method return the object if the object is still alive.
                if the object is dead it return None.
                """
                im_self = self.im_self()
                res = None
                if im_self is not None:
                        res = new.instancemethod(self.im_func, im_self, self.im_class)
                return res

        def __repr__(self):
                """
                This return the string representation of the ref
                """
                im_self = self.im_self()
                if im_self is None:
                        desc = "dead"
                else:
                        desc = repr(im_self)
                return "<weak bound method at %x; %s>" % (id(im_self), desc)
