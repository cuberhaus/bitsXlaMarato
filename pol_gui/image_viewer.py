from tkinter import *
from PIL import ImageTk, Image

root = Tk()
# We will make the title of our app as Image Viewer
root.title("Image Viewer")

# The geometry of the box which will be displayed
# on the screen
root.geometry("700x700")

# We will have three button back ,forward and exit
button_back = Button(root, text="Back", command=back,
                     state=DISABLED)

# root.quit for closing the app
button_exit = Button(root, text="Exit",
                     command=root.quit)

button_forward = Button(root, text="Forward",
                        command=lambda: forward(1))

# grid function is for placing the buttons in the frame
button_back.grid(row=5, column=0)
button_exit.grid(row=5, column=1)
button_forward.grid(row=5, column=2)

root.mainloop()