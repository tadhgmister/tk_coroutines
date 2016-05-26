import tk_routines
import numpy as np
import tkinter as tk
import random


class gui(tk.Tk):
    def __init__(self,rows=3, columns=3):
        tk.Tk.__init__(self)
        self.tiles = {}
        for row in range(columns):
            for col in range(rows):
                tile = tk.Label(self,width=2)
                tile.grid(column=col, row=row,padx=10,pady=10)
                self.tiles[row,col] = tile
            
    def update_app(self,matrix,**opts):
        for loc, tile in self.tiles.items():
            tile.config(text=matrix[loc], **opts)
    def update_cell(self,row,col,**kw):
        self.tiles[row,col].configure(**kw)

@tk_routines.Routine
def draw_stuff():
    x = np.array([[5,6,7],[2,3,4],[4,5,6]])
    app.update_app(x,fg="black")
    for i in range(3):
       for j in range(3):
           x[i][j] = random.randint(1,9)
           print(x)
           app.update_cell(i,j,text=x[i][j], fg="red")
           yield 500
    print("done!")

def main():
    app = gui()
    process = None
    def change(e=None):
        nonlocal process
        if process is None or process.finished:
            process = draw_stuff()

    app.bind("<Button-1>",change)
    app.mainloop()


if __name__ == "__main__":
    main()
