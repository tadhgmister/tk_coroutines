"""
This is a library that aims to simplify the creation of coroutines in tkinter
applications by decorating a generator function with the @Routine

when the decorated generator is called it begins immidiately unlike normal generators
when it yields control events are set up according to this specification in .actions.__doc__


### error handling ###

A fail-safe has been implemented that if / when all the widgets that can
continue the generator have been destroyed, a WidgetDestroyed error will
be thrown into the generator.
WidgetDestroyed is a subclass of tkinter.TclError and the event of the
last <Destroy> event will be available as an argument to the error



"""


import functools as _functools
import tkinter as _tk

class WidgetDestroyed(_tk.TclError):
    pass

from . import action
from . import generator


class Routine:
    _meta_data_assigned = set(_functools.WRAPPER_ASSIGNMENTS) - {"__module__"}
    def __init__(self,func):
        self._func = func
        self.__name__ = getattr(self._func, "__name__", "<NO NAME>")
    def __call__(*args,**kw):
        self,*args = args #allow self as keyword
        gen = self._func(*args,**kw)
        return generator.EventGenerator(gen)
    
    @property
    def as_sub(self):
        """use this when needed to use an Routine from within another one
for instance you would do:

    return_value = yield from OTHER_EVENT_HANDLER.as_sub(*args)

this will prevent event collision by using the generator directly
so that only the outer most handler is processing events.

Hopefully at some point we can get the generators to recognize the overlap and fix it automatically"""
        return self._func
    
    def __get__(self,inst,cls=None):
        getter = getattr(self._func, "__get__",None)
        if getter:
            return Routine(getter(inst,cls))
        else:
            return self

        
