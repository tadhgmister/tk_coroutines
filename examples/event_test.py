
import tk_routines
import tkinter as tk
from tkinter import colorchooser

root = tk.Tk()

import itertools
class BlobTest(tk.Canvas):
    """click on the canvas to draw some shapes

Handling the state of what kind of shape should be drawn next is
simple for people with experience with event based programming.
However those farmiliar with procedural code will """
    def __init__(self,window):
        tk.Canvas.__init__(self,window,width=400,height=300)
        self.draw_blobs()
        
    @tk_routines.Routine
    def draw_blobs(self):
        print("start")
        blobs = set()
        method_cycler = itertools.cycle((self.create_oval,self.create_rectangle))
        color_cycler = itertools.cycle(("turquoise","green","orange","violet","slate blue"))
        for method,color in zip(method_cycler,color_cycler):
            for id in blobs:
                self.itemconfigure(id,outline = color,width=4)
            blobs = set()
            for r in range(10,30,5):
                try:
                    e = yield {self:"<Button-1>"}
                except tk_routines.WidgetDestroyed:
                    return
                print("1")
                id = method(e.x-r, e.y-r, e.x+r, e.y+r, fill=color)
                blobs.add(id)



BUTTONS_PER_ROW = 3

tests = [BlobTest]
active_tests = {}
for i,cls in enumerate(tests):
    def start_test(cls=cls):
        if cls in active_tests and active_tests[cls].winfo_exists():
            active_tests[cls].lift()
            return
                
        window = tk.Toplevel(root)
        window.test_case = cls(window)
        window.test_case.grid()
        window.message = tk.Label(window,text=cls.__doc__)
        window.message.grid()
        active_tests[cls] = window

    button = tk.Button(root,text=cls.__name__,command=start_test)
    button.grid(row=(i//BUTTONS_PER_ROW), column=(i%BUTTONS_PER_ROW))

root.mainloop()
