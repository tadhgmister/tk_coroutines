import abc
import tkinter as tk

def _get_default_root():
    if not tk._support_default_root:
        raise RuntimeError("cannot use implied root")
    elif tk._default_root is None:
        raise RuntimeError("too early to start generator")
    else:
        return tk._default_root
    
_keywords = {}

def parse_event_spec(arg):
    if isinstance(arg,dict):
        for key, value in arg.items():
            if isinstance(key,tk.Widget):
                yield Widget_Multibind_Handler(key,value)
            elif key in _keywords:
                yield _keywords[key](value)
            else:
                raise TypeError("key in arg dict is not a widget or keyword: {!r}".format(key))
    elif not isinstance(arg,(tuple,list,set)):
        arg = (arg,)

    for item in arg:
        if isinstance(item, EventHandler):
            yield item
        elif isinstance(item, str):
            yield GlobalListener(item)
        elif isinstance(item, tk.Button):
            yield ButtonListener(item)
        elif isinstance(item, int):
            yield Delay(item)
        else:
            raise TypeError("action listener does not match any recognized spec: {!r}".format(item))


def register(keyword, listener):
    if not isinstance(keyword,str):
        raise TypeError("keyword must be a string, not {0.__class__}".format(keyword))
    elif keyword in _keywords:
        raise KeyError("key {!r} is already registered".format(keyword))
    elif not issubclass(listener, EventHandler):
        raise TypeError("listener must be a subclass of EventHandler")
    elif listener.__abstractmethods__:
        raise TypeError("listener still has abstract methods!")
    else:
        _keywords[keyword] = listener


class EventHandler(abc.ABC):
    """!! TO DO: Document the EventHandler"""
    _active = False
    def __init__(self,widget):
        "by default this takes one argument and stores it as an attribute called .widget"
        self.widget = widget

    def _setup(self,callable):
        if self._active:
            raise RuntimeError("EventHandler is already active!")
        self.setup(callable)
        self._active = True

    def _cleanup(self):
        if not self._active:
            raise RuntimeError("EventHandler is not active!")
        self.cleanup()
        self._active = False

    @abc.abstractmethod
    def setup(self, callable):
        """take a callable and set up binding for it."""
        self.id = self.widget.bind("<<Sequence>>",callable,"+")
        
    @abc.abstractmethod
    def cleanup(self):
        """called after the event triggered or the failsafe triggered,
cleans up any bindings this handler holds"""
        try:
            self.widget.unbind(self.id)
        except tk.TclError: #maybe the widget was destroyed?
            pass

    
    def get_failsafe(self):
        """returns a widget that - if destroyed - would stop this event from being triggered
this by default will return self.widget if you are also using the default __init__ but in most cases this should be overridden"""
        return self.widget


class GlobalListener(EventHandler):
    def __init__(self,binding):
        self.sequence = binding
        self.root = _get_default_root()

    def setup(self,callable):
        #XXX TO DO: add check that this will not override an existing global binding
        self.id = self.root.bind_all(self.sequence, callable)

    def cleanup(self):
        try:
            self.root.unbind_all(self.id)
        except tk.TclError:
            pass

    def get_failsafe(self):
        return self.root
    
register("bind_all", GlobalListener)
bind_all = GlobalListener


class Delay(EventHandler):
    def __init__(self,time,widget=None):
        self.wait_time = time
        if widget:
            self.widget = widget
        else:
            self.widget = _get_default_root()
        
    def setup(self,callable):
        self.id = self.widget.after(self.wait_time, callable)


    def cleanup(self):
        try:
            self.widget.after_cancel(self.id)
        except tk.TclError:
            pass

    def get_failsafe(self):
        return self.widget

register("wait",Delay)
wait = Delay


class ButtonListener(EventHandler):
    def __init__(self,widget):
        if not isinstance(widget,tk.Button):
            raise NotImplementedError("button listeners can only be created on buttons, not {0.__class__}".format(widget))
        self.widget = widget
        
    def setup(self,callable):
        self.old_command = self.widget.cget("command")
        self.final_callable = callable
        self.widget.configure(command = self.invoke)

    def invoke(self):
        self.widget.configure(command=self.old_command)
        return self.final_callable(self.widget.invoke())

    def cleanup(self):
        self.widget.configure(command=self.old_command)


class Widget_Multibind_Handler(EventHandler):
    def __init__(self, widget, sequence):
        if not isinstance(widget, tk.Widget):
            raise TypeError("widget must be a tk widget, not {0.__class__}".format(widget))
        self.widget = widget
        if isinstance(sequence,(list,tuple)):
            sequence = set(sequence)
        elif not isinstance(sequence, set):
            sequence = {sequence} #single element
        self.invoke_handler = None
        for item in sequence:
            if item == "INVOKE":
                sequence.remove(item)
                self.invoke_handler = ButtonListener(widget)
            elif not isinstance(item,str):
                raise TypeError("sequences to bind can only be strings, not {!r}".format(item))
            elif not (item.startswith("<") and item.endswith(">")):
                raise ValueError("sequence does not look like a valid for binding: {!r}".format(item))
        self.sequences = sequence

    def setup(self,callable):
        self.ids = {self.widget.bind(seq, callable,"+") for seq in self.sequences}
        if self.invoke_handler:
            self.invoke_handler.setup(callable)

    def cleanup(self):
        try:
            for id in self.ids:
                self.widget.unbind(id)
        except tk.TclError:
            pass
        if self.invoke_handler:
            self.invoke_handler.cleanup()

        
                                 
