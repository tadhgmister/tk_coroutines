import tkinter as tk
from collections import defaultdict

def debug(*stuff,sep=' ', end='\n'):
    if debug.active:
        print(__name__,*stuff,sep=sep,end=end)
debug.active = False

class Widget_Destroyed(tk.TclError):
    """exception thrown into coroutines when the widget it was waiting for was destroyed"""
    def __init__(self, event=None):
        self.event = event
        if event:
            self.widget = event.widget
        super().__init__(event)
    def __str__(self):
        return repr(self.widget)

    
class Routine_Handler:
    """
    handler for all routines in tkinter, it is intended as a singleton class
    """
    def __init__(self, Tk_inst:tk.Tk):
        self.root_app = Tk_inst
        self.root_app.bind_all("<<Advance-Coroutine>>", self.ready_to_advance)
        self.routines = defaultdict(set) #<id of awaitable>: {set of routines using that awaitable}

    def ready_to_advance(self,event=None):
        self._advance_routines(event)

    _NO_ID = object()
    
    @staticmethod
    def _process_data(event):
        if event is None:
            return None, None, False
        key = event.state
        debug("using key",key)
        stuff = event.widget._ROUTINES__temp
        info = stuff.pop(key)
        debug("GOT INFO!",info)
        return info['data'], info['id'], info['throw']
        
    def _advance_routines(self,event):
        "callback for virtual events triggered by Awaitables"
        debug("ADVANCING_ROUTINES",event)
        event, id, do_throw= self._process_data(event)
        debug((id,do_throw))
        if id not in self.routines:
            return
        
        if do_throw:
            debug("do throw is True")
            event = Widget_Destroyed(event) #use an error instead
            
        routines = self.routines.pop(id) #pop so any repeats will be put into a fresh set, no overlap!
        debug("ROUTINES is",routines)
        for r in routines:
            next_id = self._one_advance(r,event)
            if next_id is not self._NO_ID:
                self.routines[next_id].add(r)
        debug("SELF_ROUTINES is",self.routines)

    def _one_advance(self,routine, event_or_err):
        debug("ONE ADVANCE")
        try:
            if isinstance(event_or_err, Widget_Destroyed):
                debug("THROWING ERROR!")
                next_id = routine.throw(event_or_err)
            else:
                next_id = routine.send(event_or_err)
        except (StopIteration, StopAsyncIteration):
            return self._NO_ID
        else:
            return next_id
    

    def register_routine(self,routine):

        self.routines[self._NO_ID].add(routine)
        print("")
        self.root_app.after_idle(self._advance_routines, self._NO_ID)
        
