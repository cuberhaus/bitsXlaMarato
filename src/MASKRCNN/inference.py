import warnings

import numpy
import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

warnings.filterwarnings('ignore')

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
CLASS_NAMES = ['__background__', '']


# https://haochen23.github.io/2020/06/fine-tune-mask-rcnn-pytorch.html#.YsxbR-xBxH5

def get_coloured_mask(mask):
    """
    random_colour_masks
      parameters:
        - image - predicted masks
      method:
        - the masks of each predicted object is given random colour for visualization
    """
    colours = [[0, 255, 0], [0, 0, 255], [255, 0, 0], [0, 255, 255], [255, 255, 0], [255, 0, 255], [80, 70, 180],
               [250, 80, 190], [245, 145, 50], [70, 150, 250], [50, 190, 190]]
    r = np.zeros_like(mask).astype(np.uint8)
    g = np.zeros_like(mask).astype(np.uint8)
    b = np.zeros_like(mask).astype(np.uint8)
    r[mask == 1], g[mask == 1], b[mask == 1] = colours[1]
    coloured_mask = np.stack([r, g, b], axis=2)
    print(coloured_mask)
    return coloured_mask


def get_prediction(img_path, confidence, model):
    """
    get_prediction
      parameters:
        - img_path - path of the input image
        - confidence - threshold to keep the prediction or not
      method:
        - Image is obtained from the image path
        - the image is converted to image tensor using PyTorch's Transforms
        - image is passed through the model to get the predictions
        - masks, classes and bounding boxes are obtained from the model and soft masks are made binary(0 or 1) on masks
          ie: eg. segment of cat is made 1 and rest of the image is made 0

    """
    img = Image.open(img_path)
    transform = T.Compose([T.ToTensor()])
    img = transform(img)

    img = img.to(device)
    pred = model([img])
    pred_score = list(pred[0]['scores'].detach().cpu().numpy())
    try:
        pred_t = [pred_score.index(x) for x in pred_score if x > confidence][-1]
    except:
        return numpy.array([]), numpy.array([]), numpy.array([])
    masks = (pred[0]['masks'] > 0.5).squeeze().detach().cpu().numpy()
    pred_class = [CLASS_NAMES[i] for i in list(pred[0]['labels'].cpu().numpy())]
    pred_boxes = [[(i[0], i[1]), (i[2], i[3])] for i in list(pred[0]['boxes'].detach().cpu().numpy())]
    masks = masks[:pred_t + 1]
    pred_boxes = pred_boxes[:pred_t + 1]
    pred_class = pred_class[:pred_t + 1]
    if masks.shape != (1, 296, 472):
        print('Hay un fallo raro')
        return numpy.array([]), numpy.array([]), numpy.array([])
    return masks, pred_boxes, pred_class


def segment_instance(img_path, model, confidence=0.5, rect_th=2, text_size=2, text_th=2):
    """
    segment_instance
      parameters:
        - img_path - path to input image
        - confidence- confidence to keep the prediction or not
        - rect_th - rect thickness
        - text_size
        - text_th - text thickness
      method:
        - prediction is obtained by get_prediction
        - each mask is given random color
        - each mask is added to the image in the ration 1:0.8 with opencv
        - final output is displayed
    """
    masks, boxes, pred_cls = get_prediction(img_path, confidence, model)
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    rgb_mask = None
    for i in range(len(masks)):
        rgb_mask = get_coloured_mask(masks[i])
        img = cv2.addWeighted(img, 1, rgb_mask, 0.5, 0)
        # cv2.rectangle(img, boxes[i][0], boxes[i][1], color=(0, 255, 0), thickness=rect_th)
        # cv2.putText(img, pred_cls[i], boxes[i][0], cv2.FONT_HERSHEY_SIMPLEX, text_size, (0, 255, 0), thickness=text_th)
    # plt.figure(figsize=(20, 30))
    # plt.imshow(img)
    # plt.xticks([])
    # plt.yticks([])
    # plt.show()
    return img, rgb_mask


# Program To Read video
# and Extract Frames


# Function to extract frames
def Vid2Frame(path, filename):
    vid_name = filename.split('.')
    vid_name = vid_name[0]

    # Creacion carpeta frames
    full_path = (path + 'frames' + '_' + vid_name + '/')
    if (os.path.exists(full_path)):
        shutil.rmtree(full_path)
    os.mkdir(full_path)

    # Path to video file
    vidObj = cv2.VideoCapture(path + filename)

    n_frames = str(vidObj.get(cv2.CAP_PROP_FRAME_COUNT))
    n_zeros = len(n_frames) - 2

    # Used as counter variable
    count = 0

    # checks whether frames were extracted
    success, image = vidObj.read()

    while success:
        # vidObj object calls read
        # function extract frames

        crop_img = image[84:380, 54:526]
        final_image = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)

        ini_zeros = int(n_zeros - len(str(count))) * '0'
        num = ini_zeros + str(count)

        # Saves the frames with frame-count
        # print(full_path + vid_name + "_" + num +".jpg", final_image)
        cv2.imwrite(full_path + vid_name + "_" + num + ".jpg", final_image)

        count += 1

        success, image = vidObj.read()


# Program To Read video
# and Extract Frames

import cv2
import os
import shutil


# Function to extract frames
def Frame2Vid(path):
    frames = sorted(os.listdir(path))
    print(frames)
    img_array = []

    # Leer imagenes
    for x in range(0, len(frames)):
        nomArchivo = frames[x]
        dirArchivo = path + str(nomArchivo)
        img = cv2.imread(dirArchivo)
        img_array.append(img)

    # Caracteríasticas video
    name_vid = ('_').join(frames[0].split('_')[0:2])
    print(name_vid)
    name_vid = name_vid.split('.')[0]

    height, width, layers = img_array[0].shape
    size = (width, height)

    out = cv2.VideoWriter(path + name_vid + '.avi', cv2.VideoWriter_fourcc(*'DIVX'), 15, size)

    for i in range(len(img_array)):
        out.write(img_array[i])
    out.release()


from glob import glob

if __name__ == '__main__':
    Vid2Frame('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/', '601_S1.avi')
    fotos = glob('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/frames_601_S1/*.jpg')
    print(fotos)

    model = torch.load('./maratoNuevo.pt')
    model.eval()

    for i, foto in enumerate(fotos):
        print(foto)
        # set to evaluation mode
        # model = torch.load('pedestrians.pt')

        # CLASS_NAMES = ['__background__', 'Ganchito']
        device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
        model.to(device)

        foto = segment_instance(foto, model, confidence=0.90)

        cv2.imwrite('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/frames_588_short2/' + str(i) + '.jpg', foto)

    Frame2Vid('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/frames_588_short2/')