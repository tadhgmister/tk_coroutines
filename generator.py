import tkinter as _tk
import functools as _functools

from . import action
from . import WidgetDestroyed

class EventGenerator:
    def __init__(self,iterator):
        self._gen = iterator
        self.__failsafe = {}
        self.__bindings = []
        self.finished = False
        self.__executing = False
        next(self) #start immidiately
    def __hash__(self):
        return id(self)

    def __iter__(self):
        return self
    def _send_or_throw(self, arg, *EXTRA, kind, suppress_StopIteration=False):
        gen_next = getattr(self._gen,kind)
        if self.finished:
            if suppress_StopIteration:
                return
            elif hasattr(self,"return_value"):
                raise StopIteration(self.return_value)
            else:
                raise StopIteration()
        elif self.__executing:
            raise RuntimeError("generator already running")
        self.__executing = True
        self._cleanup()
        try:
            new_event_spec = gen_next(arg,*EXTRA)
        except StopIteration as e:
            self.return_value = e.value
            self.finished = True
            if not suppress_StopIteration:
                raise
        except BaseException:
            self.finished = True
            raise
        else:
            if new_event_spec is not None:
                self._handle_next_event_spec(new_event_spec)
            return new_event_spec
        finally:
            self.__executing = False
            
    send = _functools.partialmethod(_send_or_throw,kind="send")
    throw = _functools.partialmethod(_send_or_throw,kind="throw")
    __next__ = _functools.partialmethod(_send_or_throw,
                                 arg=None, kind="send")
    def send_no_raise(self,arg=None):
        return self._send_or_throw(arg,kind="send",suppress_StopIteration=True)
    
    throw_no_raise = _functools.partialmethod(_send_or_throw,kind="throw",
                                              suppress_StopIteration = True)

    def _cleanup(self):
        #XX is this check necessary?
##        if self.__executing: 
##            raise RuntimeError("generator already running")
        self._clear_failsafe()
        for handler in self.__bindings:
            handler.cleanup()
        self.__bindings.clear()

    def _clear_failsafe(self):
        for widget,id in self.__failsafe.items():
            try:
                widget.unbind("<Destroy>", id)
            except _tk.TclError:
                pass
        self.__failsafe.clear()

    def _handle_next_event_spec(self,spec):
        for action_listener in action.parse_event_spec(spec):
            self.__bindings.append(action_listener)
            action_listener.setup(self.send_no_raise)
            w = action_listener.get_failsafe()
            if w not in self.__failsafe:
                self.__failsafe[w] = w.bind("<Destroy>", self.failsafe_lost, "+")

    def failsafe_lost(self,e):
        if e.widget in self.__failsafe:
            id = self.__failsafe.pop(e.widget)
            e.widget.unbind(id)
        if not self.__failsafe:
            err = WidgetDestroyed(e)
            self.throw_no_raise(err)
        

    
            
