"""
Every time a Routine is started it creates and returns a EventGenerator object, which is defined here

"""

from tkinter import TclError
from functools import partialmethod

from . import action, WidgetDestroyed

class EventGenerator:
    """wrapper for Routine generators,
implements next(), .send and .throw like normal generators
also has .finished attribute to indicate when routine is finished
and (assuming it did not have an error) a .return_value upon finishing."""
    def __init__(self,iterator):
        """starts with a generator, note that no check is done here but is done in Routine.__call__"""
        self._gen = iterator
        self.__failsafe = {}
        self.__bindings = []
        self.finished = False
        self.__executing = False
        next(self) #start immidiately
    def __hash__(self):
        """hashes based on id"""
        return id(self)

    def __iter__(self):
        "return self"
        return self
    def _send_or_throw(self, arg, *EXTRA, kind, suppress_StopIteration=False):
        """common code between __next__, send, throw, and send_no_raise"""
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
    #these three are partial methods of above method
    send = partialmethod(_send_or_throw,kind="send")
    throw = partialmethod(_send_or_throw,kind="throw")
    __next__ = partialmethod(_send_or_throw,
                                 arg=None, kind="send")
    #this could not be a partial method since it is used for bindings and requires a __name__ to function properly
    def send_no_raise(self,arg=None):
        """implements .self(arg) but just returns None on StopIteration"""
        return self._send_or_throw(arg,kind="send",suppress_StopIteration=True)
    
    throw_no_raise = partialmethod(_send_or_throw,kind="throw",
                                              suppress_StopIteration = True)

    def _cleanup(self):
        """cleanup event handlers after one triggers"""
        #XX is this check necessary?
##        if self.__executing: 
##            raise RuntimeError("generator already running")
        self._clear_failsafe()
        for handler in self.__bindings:
            handler.cleanup()
        self.__bindings.clear()

    def _clear_failsafe(self):
        """clean up failsafe, removes <Destroy> bindings from widgets"""
        for widget,id in self.__failsafe.items():
            try:
                widget.unbind("<Destroy>", id)
            except TclError:
                pass
        self.__failsafe.clear()

    def _handle_next_event_spec(self,spec):
        """sets up next handlers"""
        for action_listener in action.parse_event_spec(spec):
            self.__bindings.append(action_listener)
            action_listener.setup(self.send_no_raise)
            w = action_listener.get_failsafe()
            if w not in self.__failsafe:
                self.__failsafe[w] = w.bind("<Destroy>", self.failsafe_lost, "+")

    def failsafe_lost(self,e):
        """called when one of the widgets that was important for the next callback was destroyed
if it was the last widget that could continue the generator a WidgetDestroyed error is thrown into the generator"""
        if e.widget in self.__failsafe:
            id = self.__failsafe.pop(e.widget)
            e.widget.unbind(id)
        else:
            from warnings import warn
            warn("failsafe was lost but not present in failsafe dict!")
        if not self.__failsafe:
            err = WidgetDestroyed(e)
            self.throw_no_raise(err)
        

    
            
