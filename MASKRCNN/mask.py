from pycocotools.coco import COCO
import os
from PIL import Image
import numpy as np
from matplotlib import pyplot as plt
%matplotlib inline

coco = COCO('/content/drive/MyDrive/Dataset/coco.json')
img_dir = '/content/drive/MyDrive/Dataset/img'
mask_dir = '/content/drive/MyDrive/Dataset/mask/'

for id in range(1, len(coco.imgs) + 1):
  img = coco.imgs[id]

  image = np.array(Image.open(os.path.join(img_dir, img['file_name'])))

  cat_ids = coco.getCatIds()
  anns_ids = coco.getAnnIds(imgIds=img['id'], catIds=cat_ids, iscrowd=None)
  anns = coco.loadAnns(anns_ids)

  #Construct the binary mask
  mask = coco.annToMask(anns[0])>0
  for i in range(len(anns)):
      mask += coco.annToMask(anns[i])>0

  plt.imshow(mask,cmap='gray')
  plt.show()
  plt.imsave(mask_dir + coco.imgs[id]['file_name'], mask, cmap='gray')
