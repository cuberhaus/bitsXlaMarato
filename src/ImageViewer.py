import tkinter as tk
from tkinter import filedialog, ttk
import cv2
from PIL import Image, ImageTk
# import MASKRCNN.inference as inf


class VideoViewer:
    def __init__(self, root):
        self.root = root
        self.video = None
        self.frame_index = 0

        # Create the image label
        self.image_label = tk.Label(root)
        self.image_label.grid(row=0, column=0, columnspan=3)

        # Create the previous frame button
        self.previous_frame_button = tk.Button(root, text="Previous Frame", command=self.previous_frame)
        self.previous_frame_button.grid(row=1, column=0)

        # Create the next frame button
        self.next_frame_button = tk.Button(root, text="Next Frame", command=self.next_frame)
        self.next_frame_button.grid(row=1, column=2)

        # Bind the arrow keys to the frame navigation functions
        self.root.bind("<Left>", self.previous_frame)
        self.root.bind("<Right>", self.next_frame)

    def previous_frame(self, event=None):
        self.frame_index -= 1

        if self.frame_index < 0:
            self.frame_index = 0
        self.show_frame()

    def next_frame(self, event=None):
        self.frame_index += 1
        if self.frame_index >= self.video.get(cv2.CAP_PROP_FRAME_COUNT):
            self.frame_index = self.video.get(cv2.CAP_PROP_FRAME_COUNT) - 1
        self.show_frame()

    def show_frame(self):
        # Set the frame index
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index)

        # Read the frame
        success, frame = self.video.read()
        if not success:
            return

        # Convert the frame to a PIL image and display it in the label
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        image = ImageTk.PhotoImage(image)
        self.image_label.configure(image=image)
        self.image_label.image = image


def load_video():
    # Open a file open dialog to select the video file
    file_path = filedialog.askopenfilename()
    if not file_path:
        return

    # Load the video file
    video = cv2.VideoCapture(file_path)

    # Set the video for the video viewer
    video_viewer.video = video

    # Display the first frame
    video_viewer.show_frame()


# Create the root window
root = tk.Tk()

root.title("Image Viewer")

# root.geometry("600x550")

# Style the buttons
style = ttk.Style()
style.configure('My.TButton', foreground='blue')

# Create the video viewer
video_viewer = VideoViewer(root)

# Create the load video button
load_video_button = ttk.Button(root, text="Load Video", style='My.TButton', command=load_video)
load_video_button.grid(row=2, column=1)

# Run the main loop
root.mainloop()
