"""
This is a library that aims to simplify procedural code working with tkinter
by the use of coroutines

## IMPORTANT NOTE ABOUT IMPLEMENTATION ##

During the lifetime of the Awaitable objects it is important they can
maintain their binding to <Delete> and the specific sequence for that object
if you unbind or rebind (without '+' flag) the sequences used in the routines
they will likely become stuck, unable to continue.

"""

# The package will be restructured at some point, not sure how yet though.

from .awaitables import Event, Click, Wait

from .handler import Widget_Destroyed, Routine_Handler
