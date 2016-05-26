import tk_routines
import itertools
import tkinter as tk
import random


@tk_routines.Routine
def animate(canvas, id):
    delay = tk_routines.action.Delay(15,canvas)
    speed = 10
    try:
        for colour in ("red","blue","green","yellow","purple"):
            canvas.itemconfigure(id, fill=colour)
            for x_inc, y_inc in ((1,0),(0,1),(-1,0),(0,-1)):
                x_inc*=speed
                y_inc*=speed
                for i in range(20):
                    canvas.move(id,x_inc,y_inc)
                    yield delay
            speed-=2
    
    except tk_routines.WidgetDestroyed:
        return
    finally:
        del animations[id]
    else:
        canvas.delete(id)


def make_box(e):
    if len(animations)>10:
        return
    x,y = e.x, e.y
    shape = e.widget.create_rectangle(x,y,x+10,y+10)
    animations[shape] = animate(e.widget, shape)

animations = {}

root = tk.Tk()

canvas = tk.Canvas(root,width=1000, height = 800)

canvas.bind("<Button-1>",make_box)

canvas.grid()

root.mainloop()
