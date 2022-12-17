import tkinter as tk
import os
from PIL import Image, ImageTk

class ImageViewer:
  def __init__(self, root, folder_path):
    self.root = root
    self.folder_path = folder_path
    self.image_paths = []
    self.images = []
    self.current_image_index = 0

    # Get a list of image paths in the specified folder
    for file in os.listdir(folder_path):
      if file.endswith(".jpg") or file.endswith(".png"):
        self.image_paths.append(os.path.join(folder_path, file))

    # Load the images
    for image_path in self.image_paths:
      image = Image.open(image_path)
      self.images.append(image)

    # Create the image label
    self.image_label = tk.Label(root)
    self.image_label.pack()

    # Create the previous image button
    self.previous_image_button = tk.Button(root, text="Previous Image", command=self.previous_image)
    self.previous_image_button.pack(side="left")

    # Create the next image button
    self.next_image_button = tk.Button(root, text="Next Image", command=self.next_image)
    self.next_image_button.pack(side="right")

    # Bind the arrow keys to the image navigation functions
    self.root.bind("<Left>", self.previous_image)
    self.root.bind("<Right>", self.next_image)
    root.title("Aorta finder")
    # Display the first image
    self.show_image()

  def previous_image(self, event=None):
    self.current_image_index -= 1
    if self.current_image_index < 0:
      self.current_image_index = len(self.images) - 1
    self.show_image()

  def next_image(self, event=None):
    self.current_image_index += 1
    if self.current_image_index >= len(self.images):
      self.current_image_index = 0
    self.show_image()

  def show_image(self):
    image = self.images[self.current_image_index]
    image = ImageTk.PhotoImage(image)
    self.image_label.configure(image=image)
    self.image_label.image = image

# Create the root window
root = tk.Tk()

# Specify the folder path
folder_path = "603_frames/S1"


# Create the image viewer
image_viewer = ImageViewer(root, folder_path)

# Run the main loop
root.mainloop()
