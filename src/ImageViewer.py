import os
import tkinter as tk
from tkinter import filedialog, ttk

from PIL import ImageTk

from MASKRCNN.inference import *

import cv2
import matplotlib.pyplot as plt
import os
import shutil
import meshlib.mrmeshpy as mr
import open3d as o3d


# Function to extract frames
def get3Dfigure(path):
    settings = mr.LoadingTiffSettings()
    # load images from specified directory
    settings.dir = path
    # specifiy size of 3D image element
    settings.voxelSize = mr.Vector3f(1, 1, 1)
    # create voxel object from the series of images
    volume = mr.loadTiffDir(settings)
    # define ISO value to build surface
    iso = 127.0
    # convert voxel object to mesh
    mesh = mr.gridToMesh(volume.value(), iso)
    # save mesh to .stl file
    mr.saveMesh(mesh.value(), mr.Path(path + "mesh3D.stl"))


def visualize(mesh):
    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(mesh)
    vis.run()
    vis.destroy_window()


def inference(path_input, video, images_expression, path_output, path_model):
    path_mascara = path_output + 'mascara/'
    global path_mask
    path_mask = path_mascara
    if os.path.exists(path_output):
        shutil.rmtree(path_output)

    try:
        os.mkdir(path_output)
    except OSError as error:
        print(error)
    try:
        os.mkdir(path_mascara)
    except OSError as error:
        print(error)

    Vid2Frame(path_input, video)
    fotos = glob(images_expression)
    model_aorta = torch.load('%s' % path_model)
    model_aorta.eval()
    model_aorta.to(device)

    n_frames = str(len(fotos))
    n_zeros = len(n_frames)
    # Used as counter variable
    count = 0

    for i, foto in enumerate(fotos):
        ini_zeros = int(n_zeros - len(str(count))) * '0'
        num = ini_zeros + str(count)
        # set to evaluation mode
        CLASS_NAMES = ['__background__', '']
        temporal, mascara = segment_instance(foto, model_aorta, confidence=0.90)
        cv2.imwrite(path_output + str(num) + '.jpg', temporal)
        if not mascara is None:
            cv2.imwrite(path_mascara + str(num) + '.tiff', mascara)
        count += 1
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
# print(os.path.expanduser('~'))
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
    path_model = script_path + '/../models/maratoNuevo.pt'
    # path_model = 'C:/Users/pable/Documents/GitHub/bitsXlaMarato/MASKRCNN/maratoNuevo.pt'
    # print(path_input)
    # print(video)
    # print(video_no_ext)
    # print(images_expression)
    # print(path_output)
    # print(path_model)

    inference(path_input=path_input, video=video, images_expression=images_expression,
              path_output=path_output,
              path_model=path_model)
    video_l = glob(path_output + '*.avi')
    if len(video_l) == 0:
        print('No se ha podido generar el video')
        return
    path_video_out = video_l[0]
    # # Load the video file
    video = cv2.VideoCapture(path_video_out)
    #
    # # Set the video for the video viewer
    video_viewer.video = video
    #
    # # Display the first frame
    video_viewer.show_frame()

def create_3d_model():
    print(path_mask)
    fotos = glob(path_mask + "*.tiff")
    print(fotos)
    for foto in fotos:
        img = Image.open(foto)
        data = np.array(img)
        binarizada = data[:, :, 0]
        nueva = Image.fromarray(binarizada)
        cv2.imwrite(foto, binarizada)
    # dir donde estan las tiff
    ruta = path_mask
    try:
        os.remove(ruta + 'mesh3D.stl')
    except:
        pass
    print(ruta)
    get3Dfigure(ruta)


    mesh = o3d.io.read_triangle_mesh(ruta + 'mesh3D.stl')
    mesh.paint_uniform_color([252 / 255, 3 / 255, 115 / 255])
    mesh.compute_vertex_normals()
    visualize(mesh)
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
