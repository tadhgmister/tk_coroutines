
import functools as _functools
import tkinter as _tk


class WidgetDestroyed(_tk.TclError):
    pass

from . import action
from . import generator


class Routine:
    def __init__(self,func):
        self._func = func
        _functools.update_wrapper(func, self)
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

        
