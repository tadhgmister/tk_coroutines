import tkinter as tk


def debug(*stuff,sep=' ', end='\n'):
    if debug.active:
        print(__name__,*stuff,sep=sep,end=end)
debug.active = False


def unbind(self, sequence, funcid=None):
    """Unbind for this widget for event SEQUENCE  the
    function identified with FUNCID."""
    #copied directly from http://stackoverflow.com/a/23921363/5827215
    if not funcid:
        self.tk.call('bind', self._w, sequence, '')
        return
    func_callbacks = self.tk.call('bind', self._w, sequence, None).split('\n')
    new_callbacks = [l for l in func_callbacks if l[6:6 + len(funcid)] != funcid]
    self.tk.call('bind', self._w, sequence, '\n'.join(new_callbacks))
    self.deletecommand(funcid)

class Tk_awaitable:
    """base class for awaitable events"""
    _active = False
    _del_event = None

    @property
    def active(self):
        return self._active
    @active.setter
    def active(self,value):
        if value and self._del_event is not None:
            raise Widget_Destroyed(self._del_event)
        else:
            self._active = value
            
    def _deleted(self,event):
        self._del_event = event
        return self._callback(event, deleted=True)
        
    def __await__(self):
        self.active = True
        a = (yield id(self))
        self.active = False
        return a

    
    ## THIS IS AN AWEFUL WAY TO GET DATA BACK TO THE HANDLER!
    # I am using self.widget._ROUTINES__temp to store a dictionary
    # that contains temperary storage for the event details,
    # then the key that was used to store the temp data is passed as the state
    # to the virtual event trigger so it knows how to retrieve the data
    # I would very much like to just pass something with data=... but it seems
    # that it isn't supported in python, so I am resorting to hacks.
    # hopefully I'll be able to find a legitamate way to transmite data.
    def _callback(self,event=None, deleted=False): 
        if not self.active:
            return
        #if the widget was destroyed we can't use it to generate the virtual event
        #so in that case we need to hand things over to the default root and hope it works
        if self.widget.winfo_exists():
            widget = self.widget
        else:
            widget = tk._default_root
        debug("in callback, event is",event)
        params = {'id' : id(self),
                  'throw' : deleted,
                  'data':event}
        hack = self.__attach_data_to_widget(params, widget)
##        debug("\n\n     ! STARTING EVENT !  STATE IS %d  \n\n"%hack)
        #sometimes it seems to ignore the event_generate so update idle tasks first
        widget.update_idletasks()
        widget.event_generate("<<Advance-Coroutine>>", state=hack)
        debug("CALLED EVENT")
        
    @staticmethod
    def __attach_data_to_widget(data, widget):
        # as far as I can tell there should only be one value ever stored at a time
        # I still want to make this fool proof and pop out the data once it is finished
        temp =  getattr(widget, "_ROUTINES__temp", None)
        if temp is None:
            temp = widget._ROUTINES__temp = {}
        for i in range(5,20): #5,7 is arbitrary, just don't want to use 0 since it is default
            if i not in temp:
                temp[i] = data
                debug("TEMP DATA IS",temp)
                return i
        else:
            raise RuntimeError("15 temperary events are in limbo, something is wrong")
            
        


class Event(Tk_awaitable):
    DESTROY = "<Destroy>"
    def __init__(self, widget, sequence):
        self.widget = widget
        self.sequence = sequence
        self.call_id = self.widget.bind(sequence, self._callback, '+')
        self.del_id = self.widget.bind(self.DESTROY, self._deleted, '+')

    def __del__(self):
        "clean up bindings here"
        try:
            unbind(self.widget, self.sequence, self.call_id)
            unbind(self.widget, self.DESTROY, self.del_id)
        except (tk.TclError, AttributeError):
            pass


class Click(Event):
    def __init__(self, widget, num=1):
        """waits for a <Button-#> event on the widget specified where # is 'num' argument"""
        super().__init__(widget, "<Button-{}>".format(num))

class Wait(Tk_awaitable):
    active = True #wait doesn't need this check since it does binding inside await
    def __init__(self,ms, widget=None):
        self.time = ms
        if widget is not None:
            self.widget = widget
        elif not tk._support_default_root:
            raise Exception('''cannot infer widget - tkinter's "support default root" flag is off''')
        elif tk._default_root is None:
            raise Exception("cannot infer widget - no Tk instance is made yet")
        else:
            self.widget = tk._default_root

    def __await__(self):
        debug("IN AWAIT")
        self.widget.after(self.time, self._callback)
        result = (yield id(self))
        debug("FINISHED AWAIT")
        return result

    
