import tkinter as tk
from tkinter import filedialog, ttk
import cv2
from PIL import Image, ImageTk
from MASKRCNN.inference import *
import os


def inference(path_input, video, images_expression, path_output, path_model):
    try:
        os.mkdir(path_output)
    except OSError as error:
        print(error)

    Vid2Frame(path_input, video)
    fotos = glob(images_expression)
    print(fotos)
    model_aorta = torch.load('%s' % path_model)
    model_aorta.eval()
    model_aorta.to(device)
    for i, foto in enumerate(fotos):
        # set to evaluation mode
        CLASS_NAMES = ['__background__', '']
        foto = segment_instance(foto, model_aorta, confidence=0.90)
        cv2.imwrite(path_output + str(i) + '.jpg', foto)
    Frame2Vid('%s' % path_output)


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


# Python get home directory using os module
print(os.path.expanduser('~'))
home = os.path.expanduser('~')


def load_video():
    # Open a file open dialog to select the video file
    file_path = filedialog.askopenfilename()
    if not file_path:
        return

    path_input = os.path.dirname(file_path)
    video = os.path.basename(file_path)
    video_no_ext = video.split('.')[0]
    images_expression = path_input + "/frames_" + video_no_ext + "/" + "*.jpg"
    path_output = path_input + "/output_" + video_no_ext + "/"
    # cwd = os.getcwd()
    script_path = os.path.realpath(os.path.dirname(__file__))
    path_model = script_path + '/../models/marato.pt'
    # print(path_input)
    # print(video)
    # print(video_no_ext)
    # print(images_expression)
    # print(path_output)
    print(path_model)

    inference(path_input=path_input, video=video, images_expression=images_expression,
              path_output=path_output,
              path_model=path_model)

    # # Load the video file
    # video = cv2.VideoCapture(file_path)
    #
    # # Set the video for the video viewer
    # video_viewer.video = video
    #
    # # Display the first frame
    # video_viewer.show_frame()

def create_3d_model():

    return


if __name__ == '__main__':
    # Create the root window
    root = tk.Tk()

    # Window title
    root.title("Aorta Viewer")

    # Window icon
    icon = tk.PhotoImage(file='logo.png')
    root.wm_iconphoto(True, icon)

    # root.geometry("600x550")

    # Style the buttons
    style = ttk.Style()
    style.configure('My.TButton', foreground='blue')

    # Create the video viewer
    video_viewer = VideoViewer(root)

    # Create the load video button
    load_video_button = ttk.Button(root, text="Load Video", style='My.TButton', command=load_video)
    load_video_button.grid(row=2, column=1)

    ThreeD_button = ttk.Button(root, text="3D", style='My.TButton', command=create_3d_model)
    ThreeD_button.grid(row=3, column=1)

    # Run the main loop
    root.mainloop()
