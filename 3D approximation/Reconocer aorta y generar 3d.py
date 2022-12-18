#!/usr/bin/env python
# coding: utf-8

# In[3]:


# Program To Read video
# and Extract Frames
 
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
    settings.dir=path
    # specifiy size of 3D image element
    settings.voxelSize=mr.Vector3f(1,1,1)
    #create voxel object from the series of images
    volume=mr.loadTiffDir(settings)
    #define ISO value to build surface
    iso=127.0
    #convert voxel object to mesh
    mesh=mr.gridToMesh(volume.value(), iso)
    #save mesh to .stl file
    mr.saveMesh(mesh.value(), mr.Path(path+"mesh3D.stl"))

def visualize(mesh):
    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(mesh)
    vis.run()
    vis.destroy_window()

    
 
# Driver Code
if __name__ == '__main__':
    
 
    # dir donde estan las tiff
    ruta = 'C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/mascara/'
    os.remove(ruta + 'mesh3D.stl')
    get3Dfigure(ruta)
    
    mesh = o3d.io.read_triangle_mesh(ruta + 'mesh3D.stl')
    mesh.paint_uniform_color([252/255, 3/255, 115/255])
    mesh.compute_vertex_normals()
    visualize(mesh)
    
    


# In[3]:


get_ipython().system('pip install open3d')


# In[ ]:


get_ipython().system('pip install meshlib')


# In[11]:


from PIL import Image
import numpy as np


# In[7]:


img = Image.open('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/mascara/27.tiff')


# In[10]:


from glob import


# In[12]:


data = np.array(img)


# In[13]:


data.shape


# In[20]:


from glob import glob
fotos = glob('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/mascara/*.tiff')


# In[41]:


for foto in fotos:
    img = Image.open(foto)
    data = np.array(img)
    binarizada = data[:, :, 0]
    nueva = Image.fromarray(binarizada)
    cv2.imwrite(foto, binarizada)


# In[42]:


Image.fromarray(binarizada)


# In[24]:


binarizada.shape


# In[32]:


img = Image.open('C:/Users/pable/Documents/GitHub/bitsXlaMarato/videos/mascara/1.tiff')


# In[34]:


np.array(img).shape


# In[ ]:




