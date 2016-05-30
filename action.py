"""
Contains all EventHandler classes for handling the events in between Routines

There are four classes (as well as the abstract EventHandler) that are included by default:

1. GlobalListener: takes a sequence binding and triggers when any widget triggers that sequence

2. WidgetMultibindHandler: takes a widget and binding or sequence of bindings and triggers when any of those sequences trigger on that widget

3. ButtonListener: takes a button widget and triggers when that button is invoked

4. Delay: takes an integer (time in milliseconds) triggers after the given time

In addition to explicitly creating these handlers you can yield 

a dict of (widget: bindings) to apply bindings to specific widgets
           and/ or
          (keyword:argument) for any keyword in action.keywords
                             by default the available keywords are {"wait":Delay, "bind_all":GlobalListener}

for example:
    yield {"wait":1000, canvas:"<Button-1>"}

would be equivelent to:
    yield action.Delay(1000), action.WidgetMultibindHandler(canvas,"<Button-1>")


as well integers will be interpreted as Delays and buttons as button listeners.
"""

import abc
import tkinter as tk

def _get_default_root():
    """used by global listeners, gets the default root of tkinter"""
    if not tk._support_default_root:
        raise RuntimeError("cannot use implied root")
    elif tk._default_root is None:
        raise RuntimeError("too early to start generator")
    else:
        return tk._default_root
    
keywords = {}

def parse_event_spec(arg):
    """used to parse the value that is gnerated by Routines, generates EventHandlers objects"""
    if isinstance(arg,dict):
        for key, value in arg.items():
            if isinstance(key,tk.Widget):
                yield WidgetMultibindHandler(key,value)
            elif key in _keywords:
                yield _keywords[key](value)
            else:
                raise TypeError("key in arg dict is not a widget or keyword: {!r}".format(key))
        return
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
    """registers a keyword that can be used when using dictionaries to specify next event
This makes various checks before doing `keywords[keyword] = listener` and is the prefered
method of registering new keywords then modifying `keywords` directly."""
    if not isinstance(keyword,str):
        raise TypeError("keyword must be a string, not {0.__class__}".format(keyword))
    elif keyword in keywords:
        raise KeyError("key {!r} is already registered".format(keyword))
    elif not issubclass(listener, EventHandler):
        raise TypeError("listener must be a subclass of EventHandler")
    elif listener.__abstractmethods__:
        raise TypeError("listener still has abstract methods!")
    else:
        keywords[keyword] = listener


class EventHandler(abc.ABC):
    """Abstract base for event handlers/listeners
subclasses must define a _setup and _cleanup
and should override get_failsafe if the widget the listener relies on is not stored as .widget attribute"""
    _active = False
    def __init__(self,widget):
        "by default this takes one argument and stores it as an attribute called .widget"
        self.widget = widget

    def setup(self,callable):
        """handles self._active to ensure one listener is not used by more then one thing at once

DO NOT OVERRIDE IN SUBCLASS! override _setup instead!"""
        if self._active:
            raise RuntimeError("EventHandler is already active!")
        self._setup(callable)
        self._active = True

    def cleanup(self):
        """handles self._active to ensure one listener is not used by more then one thing at once

DO NOT OVERRIDE IN SUBCLASS! Override _cleanup instead!"""
        if not self._active:
            raise RuntimeError("EventHandler is not active!")
        self._cleanup()
        self._active = False

    @abc.abstractmethod
    def _setup(self, callable):
        """take a callable and set up binding for it."""
        self.id = self.widget.bind("<<Sequence>>",callable,"+")
        
    @abc.abstractmethod
    def _cleanup(self):
        """called after the event triggered or the failsafe triggered,
cleans up any bindings this handler holds,
note that the relevent widget may have been destroyed, handle errors appropriately."""
        try:
            self.widget.unbind(self.seq, self.id)
        except tk.TclError: #maybe the widget was destroyed?
            pass

    
    def get_failsafe(self):
        """returns a widget that - if destroyed - would stop this event from being triggered
this by default will return self.widget if you are also using the default __init__ but in most cases this should be overridden"""
        return self.widget


class GlobalListener(EventHandler):
    """given a binding string continues the Routine when any widget triggers that event."""
    def __init__(self,binding):
        self.sequence = binding
        self.root = _get_default_root()

    def _setup(self,callable):
        #XXX TO DO: add check that this will not override an existing global binding
        self.id = self.root.bind_all(self.sequence, callable)

    def _cleanup(self):
        try:
            self.root.unbind_all(self.id)
        except tk.TclError:
            pass

    def get_failsafe(self):
        return self.root
    
register("bind_all", GlobalListener)
bind_all = GlobalListener


class Delay(EventHandler):
    """given a time (as int) in milliseconds triggers after that amount of time."""
    def __init__(self,time,widget=None):
        """if the widget given then .after is used on that widget,
otherwise it is used on the root window."""
        self.wait_time = time
        if widget:
            self.widget = widget
        else:
            self.widget = _get_default_root()
        
    def _setup(self,callable):
        self.id = self.widget.after(self.wait_time, callable)


    def _cleanup(self):
        try:
            self.widget.after_cancel(self.id)
        except tk.TclError:
            pass

    def get_failsafe(self):
        return self.widget

register("wait",Delay)
wait = Delay


class ButtonListener(EventHandler):
    """given a button triggers when button is invoked"""
    def __init__(self,widget):
        if not isinstance(widget,tk.Button):
            raise NotImplementedError("button listeners can only be created on buttons, not {0.__class__}".format(widget))
        self.widget = widget
        
    def _setup(self,callable):
        #note that this saves the original command and overrides the one of the button
        self.old_command = self.widget.cget("command")
        self.final_callable = callable
        self.widget.configure(command = self.invoke)

    def invoke(self):
        #restore the original command and then pass it's return value to the final_callable
        #this means that the button gets invoked while handling the button getting invoked
        #it does not seem to be an issue but it could result in bugs
        self.widget.configure(command=self.old_command)
        return self.final_callable(self.widget.invoke())

    def _cleanup(self):
        self.widget.configure(command=self.old_command)

#the reason this is called Multibind is because it also supports buttons having an 'INVOKE' sequence to handle it being invoked
# this may need to expand if other special terms are used.
class WidgetMultibindHandler(EventHandler):
    """handles a number of bindings for a single widget,
can also take a special 'INVOKE' sequence for buttons, may take other special sequences in the future."""
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

    def _setup(self,callable):
        self.ids = {(seq, self.widget.bind(seq, callable,"+")) for seq in self.sequences}
        if self.invoke_handler:
            self.invoke_handler.setup(callable)

    def _cleanup(self):
        for seq,bind_id in self.ids:
            try:
                self.widget.unbind(seq,bind_id)
            except tk.TclError:
                pass
        if self.invoke_handler:
            self.invoke_handler.cleanup()

        
                                 
