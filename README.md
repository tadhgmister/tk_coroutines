# tk_routines

THIS PACKAGE IS DEPRECATED WITH NO INTENT TO REPLACE IT

This package was an attempt to have a bridge from imperative coding styles to work relatively seamlessly in a tk event loop.  The goal was to use `await` to pause functions to wait until some tk event to resume them. 
This was initially build on just `yield` and iterator constructs, only to be updated to just use `await` later. Because of this a lot of the excellent features of await are totally lost and would require significant re-write to fix.

At some point I know I had examples that used the library but they don't seem to be commited, I abandoned this package because a lot of the things it uses are pretty unsound for production code and a lot of the event handling is very inefficiently done to try to account for maximum flexibility.  This is to the point where running an animation, moving a figure across a canvas, works nicely but the moment you have about 10 of these animations running things start slowing down a lot. and 10 animations isn't very scalable in the long run. 

I have moved to other languages, particularly typescript, and javascript applications have significantly better handling for these kinds of GUI elements since async and promise handling is far easier to do when the event loop of the browser just handles them natively so I don't really see much point in trying to revive this package ever.
