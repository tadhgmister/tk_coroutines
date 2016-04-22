"""
This is a library that aims to simplify the creation of coroutines in tkinter
applications by decorating a generator function with the @EventCoroutine

when the decorated generator is called it begins immidiately unlike normal generators
when it yields control events are set up according to this specification:

### event spec ###
this is the notation that is used at 'yield' statements to indicate the event(s)
that will trigger the next step in the generator

1. event sequence as str

e = yield "<Key-Escape>"

waits until the sequence is triggered by any widget
the Event object that triggers the callback is returned from the yield
if there is already a binding to that sequence an AssertionError is raised


2. tkinter.Button instance

b = tkinter.Button(..., command=(lambda:"RESULT"))
result = yield b

waits until the button is pressed
the return value of the original command is returned from yield
if there was no command on the button then None will be returned

3. a tuple or set of any combination of case 1. and 2.

b = tkinter.Button(..., command=(lambda:"ButtonPressed"))
result = yield b,"<Key-Escape>"
if result == "ButtonPressed":
    # Process for button
else:
    # Process for escape

Waits until any of the conditions are triggered
returns the expected result from the condition that triggered

4. a dict of {widget: sequence} pairs

e = yield {canvas:("<Button-1>","<Button-2>"), window:"<Destroy>"}

each value is either a single sequence or a tuple (or set) of sequences to bind
to that single widget.  There are two special values that can be used:

 - Button widgets can use the sequence "INVOKE" to indicate
   that the generator should continue when invoked
 - A key of "bind_all" is allowed to indicate to create bindings to all widgets

### error handling ###

A fail-safe has been implemented that if / when all the widgets that can
continue the generator have been destroyed, a WidgetDestroyed error will
be thrown into the generator.
WidgetDestroyed is a subclass of tkinter.TclError and the event of the
last <Destroy> evnet will be available as an argument to the error



"""

import tkinter as tk
import functools

_do_nothing = (lambda:None)

class WidgetDestroyed(tk.TclError):
    pass

def parse_event_spec(arg,context=None):
    #note to self: context is the widget when parsing values of dicts
    if isinstance(arg,str):
        yield (context or "bind_all"), arg
    elif isinstance(arg,tk.Button) and context is None:
        yield arg,"INVOKE"
    elif isinstance(arg,(tuple,set)):
        for i in arg:
            if isinstance(i,str):
                yield context, i
            elif isinstance(i,tk.Button) and context is None:
                yield i,"INVOKE"
            else:
                invalid_type = TypeError("cannot nest {0.__class__.__name__!r} in event spec".format(i))
                raise invalid_type
            
    elif isinstance(arg,dict):
        if context is not None:
            raise TypeError("cannot nest 'dict' in event spec")
        for w,sub_arg in arg.items():
            if w != "bind_all" and not isinstance(w,tk.Misc):
                invalid_type = TypeError("all keys of dict must be widgets or 'bind_all', not {0.__class__}".format(w))
                raise invalid_type
            for i in parse_event_spec(sub_arg,w):
                yield i
    else:
        invalid_type = TypeError("event spec cannot be a {0.__class__.__name__!r}".format(arg))
        raise invalid_type


def get_default_root():
    if not tk._support_default_root:
        raise RuntimeError("cannot use implied root")
    elif tk._default_root is None:
        raise RuntimeError("too early to start generator")
    else:
        return tk._default_root

class BoolFlag:
    def __init__(self):
        self.__state = False
    def __enter__(self):
        if self.__state:
            raise ValueError("generator already executing")
        self.__state = True
        return self
    def __exit__(self,*args):
        self.__state = False

class EventGenerator:
    def __init__(self,iterator):
        self._gen = iterator
        self.__failsafe = None
        self.__bindings = None
        self.finished = False
        self.__executing = BoolFlag()
        next(self) #start immidiately

    def __iter__(self):
        return self
    def _send_or_throw(self,arg,*EXTRA,kind):
        gen_next = getattr(self._gen,kind)
        if self.finished:
            raise StopIteration(self.return_value)
        with self.__executing:
            self._cleanup()
            try:
                new_event_spec = gen_next(arg,*EXTRA)
            except StopIteration as e:
                self.return_value = e.value
                self.finished = True
                raise
            except BaseException:
                self.finished = True
                raise
            else:
                if new_event_spec is not None:
                    self._handle_next_event_spec(new_event_spec)
                return new_event_spec
            
    send = functools.partialmethod(_send_or_throw,kind="send")
    throw = functools.partialmethod(_send_or_throw,kind="throw")
    __next__ = functools.partialmethod(_send_or_throw,
                                 arg=None, kind="send")
    def send_no_raise(self,arg):
        "calls self.send(arg) but supresses StopIteration, used for iternal binding"
        try:return self.send(arg)
        except StopIteration:pass
        
    def _cleanup(self):
        if self.__failsafe:
            self.__failsafe.clear()
            self.__failsafe = None
        if self.__bindings:
            for id,(w,seq) in self.__bindings.items():
                try:
                    if isinstance(w,tk.Button) and seq == "INVOKE":
                        # in this case the wrapper command is the id
                        # and the old one is stored as id.old
                        w.configure(command=id.old)
                    elif w=="bind_all":
                        get_default_root().unbind_all(seq)
                    else:
                        w.unbind(seq,id)
                except tk.TclError:
                    pass
            self.__bindings.clear()
            self.__bindings = None

    def _handle_next_event_spec(self,event_spec):
        root = None
        self.__failsafe = FailSafe(self)
        self.__bindings = {}
        for w,seq in parse_event_spec(event_spec):
            if w == "bind_all":
                if root is None:
                    root = get_default_root()
                assert not root.bind_all(seq),"Binding collision %r"%seq
                id = root.bind_all(seq,self.send_no_raise)
            elif isinstance(w,tk.Button) and seq == "INVOKE":
                old_command = w.cget("command")
                def wrapper_command(button=w,old_command=old_command):
                    button["command"] = old_command
                    result = button.invoke()
                    self.send_no_raise(result)
                    return result
                w.configure(command=wrapper_command)
                #this is to ensure that the id is unique and
                #simplify the machanics for retrieving the old command
                id = wrapper_command
                id.old = old_command 
            else:
                id = w.bind(seq,self.send_no_raise,"+")
            self.__bindings[id] = (w,seq)
            
            if seq == "<Destroy>": #no need for failsafe
                self.__failsafe.clear() #this also sets it to obsolete so no future ones get added
            elif w=="bind_all":
                self.__failsafe.add(root)
            else:
                self.__failsafe.add(w)
        if self.__failsafe.obsolete:
            self.__failsafe = None #this probably isn't necessary but it reduces clutter

class FailSafe(dict):
    def __init__(self,gen):
        self.obsolete = False
        self.gen = gen
        dict.__init__(self)

    def clear(self):
        self.obsolete = True
        for w,id in self.items():
            w.unbind("<Destroy>",id)
        dict.clear(self)

    def add(self,w):
        if w not in self and not self.obsolete:
            self[w] = w.bind("<Destroy>",self.remove,"+")

    def remove(self,e):
        print("running remove",id(self))
        if self.obsolete:
            print("OBSOLETE")
            return
        e.widget.unbind("<Destroy>",self[e.widget])
        del self[e.widget]
        if len(self)==0:
            gen = self.gen
            del self.gen #remove reference from self
            self.clear()
            try:
                gen.throw(WidgetDestroyed(e))
            except StopIteration:
                pass



class EventCoroutine:
    def __init__(self,func):
        self._func = func
        functools.wraps(func)(self) #copy metadata
    def __call__(*args,**kw):
        self,*args = args #allow self as keyword
        gen = self._func(*args,**kw)
        return EventGenerator(gen)
    
    @property
    def as_sub(self):
        """use this when needed to use an EventGeneratorHandler from within another one
for instance you would do:

    return_value = yield from OTHER_EVENT_HANDLER.as_sub(*args)

this will prevent event collision by using the generator directly
so that only the outer most handler is processing events."""
        return self._func
    
    def __get__(self,inst,cls=None):
        return BoundEventHandler(self,inst)

class BoundEventHandler:
    def __init__(self,event_handler,inst):
        self._event_handler = event_handler
        self.inst = inst
    def __call__(*args,**kw):
        self,*args = args
        return self._event_handler(self.inst,*args,**kw)
    def as_sub(*args,**kw):
        self,*args = args
        return self._event_handler.as_sub(self.inst,*args,**kw)

