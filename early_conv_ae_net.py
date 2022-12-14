# -*- coding: utf-8 -*-
"""Early_Conv_AE_Net

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rE4R1Pw0DKdTmiGWusfUx7grpzbjs9UX
"""

# install TensorFlow 2.0 
# !pip install tensorflow

# Commented out IPython magic to ensure Python compatibility.
from os.path import dirname, join as pjoin
import datetime, os
from scipy.signal import correlate,filtfilt,butter
from scipy.io import wavfile
import matplotlib.pyplot as plt
import numpy as np
import glob
import cv2
import time
import random
from torch.utils.data.dataset import Dataset
import torch.nn.functional as F
import torch.nn as nn
from torch.utils.data import DataLoader
import torch
from torch.utils.tensorboard import SummaryWriter
import torch.utils.tensorboard as tb
import tempfile
import torchvision.utils as vutils
import matplotlib.pyplot as plt
import math
import tempfile
import h5py
import seaborn as sns
# %load_ext tensorboard
# %tensorboard --logdir=runs
log_dir = tempfile.mkdtemp()
from google.colab import drive
drive.mount('/content/drive')
# %tensorboard --logdir logs
# tensorboard --logdir=runs
# %tensorboard --logdir {log_dir} --reload_interval 1

class decode_block(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, padding):
        super(decode_block, self).__init__()
        self.up_conv = nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, kernel_size, stride = stride, padding=padding),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2, True)
        )
        
    def forward(self, x):
        x = self.up_conv(x)
        # print(len(x))
        return x

### Audio Subnetwork

class SoundNet(nn.Module):
    def __init__(self):
        super(SoundNet, self).__init__()

        self.conv1 = nn.Conv2d(2, 16, kernel_size=(64, 1), stride=(2, 1),
                               padding=(32, 0))
        self.batchnorm1 = nn.BatchNorm2d(16, eps=1e-5, momentum=0.1)
        self.relu1 = nn.ReLU(True)
        self.maxpool1 = nn.MaxPool2d((8, 1), stride=(8, 1))

        self.conv2 = nn.Conv2d(16, 32, kernel_size=(32, 1), stride=(2, 1),
                               padding=(16, 0))
        self.batchnorm2 = nn.BatchNorm2d(32, eps=1e-5, momentum=0.1)
        self.relu2 = nn.ReLU(True)
        self.maxpool2 = nn.MaxPool2d((8, 1), stride=(8, 1))

        self.conv3 = nn.Conv2d(32, 64, kernel_size=(16, 1), stride=(2, 1),
                               padding=(8, 0))
        self.batchnorm3 = nn.BatchNorm2d(64, eps=1e-5, momentum=0.1)
        self.relu3 = nn.ReLU(True)

        self.conv4 = nn.Conv2d(64, 128, kernel_size=(8, 1), stride=(2, 1),
                               padding=(4, 0))
        self.batchnorm4 = nn.BatchNorm2d(128, eps=1e-5, momentum=0.1)
        self.relu4 = nn.ReLU(True)

        self.conv5 = nn.Conv2d(128, 256, kernel_size=(4, 1), stride=(2, 1),
                               padding=(2, 0))
        self.batchnorm5 = nn.BatchNorm2d(256, eps=1e-5, momentum=0.1)
        self.relu5 = nn.ReLU(True)
        self.maxpool5 = nn.MaxPool2d((2, 1), stride=(2, 1))

        self.conv6 = nn.Conv2d(256, 512, kernel_size=(4, 1), stride=(2, 1),
                               padding=(2, 0))
        self.batchnorm6 = nn.BatchNorm2d(512, eps=1e-5, momentum=0.1)
        self.relu6 = nn.ReLU(True)

        self.conv7 = nn.Conv2d(512, 512, kernel_size=(4, 1), stride=(2, 1),
                               padding=(2, 0))
        self.batchnorm7 = nn.BatchNorm2d(512, eps=1e-5, momentum=0.1)
        self.relu7 = nn.ReLU(True)

    def forward(self, x1, x2):
        x0 = torch.cat([x1,x2],1)
        x = self.conv1(x0)
        x = self.batchnorm1(x)
        x = self.relu1(x)
        x = self.maxpool1(x)

        x = self.conv2(x)
        x = self.batchnorm2(x)
        x = self.relu2(x)
        x = self.maxpool2(x)

        x = self.conv3(x)
        x = self.batchnorm3(x)
        x = self.relu3(x)

        x = self.conv4(x)
        x = self.batchnorm4(x)
        x = self.relu4(x)

        x = self.conv5(x)
        x = self.batchnorm5(x)
        x = self.relu5(x)
        x = self.maxpool5(x)

        x = self.conv6(x)
        x = self.batchnorm6(x)
        x = self.relu6(x)

        x = self.conv7(x)
        x = self.batchnorm7(x)
        x = self.relu7(x)

        return x

### Visual Subnetwork

import torchvision.models as models
model_image = models.vgg16(pretrained=True)

class VGG16(nn.Module):

    def __init__(self, num_classes):
      super(VGG16, self).__init__()

        # calculate same padding:
        # (w - k + 2*p)/s + 1 = o
        # => p = (s(o-1) - w + k)/2

      self.block_1 = nn.Sequential(
            nn.Conv2d(in_channels=3,
                      out_channels=64,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      # (1(32-1)- 32 + 3)/2 = 1
                      padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(in_channels=64,
                      out_channels=64,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                         stride=(2, 2))
        )

      self.block_2 = nn.Sequential(
            nn.Conv2d(in_channels=64,
                      out_channels=128,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.Conv2d(in_channels=128,
                      out_channels=128,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                         stride=(2, 2))
        )
        
      self.block_3 = nn.Sequential(
            nn.Conv2d(in_channels=128,
                      out_channels=256,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(in_channels=256,
                      out_channels=256,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.Conv2d(in_channels=256,
                      out_channels=256,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                         stride=(2, 2))
        )

      self.block_4 = nn.Sequential(
            nn.Conv2d(in_channels=256,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                         stride=(2, 2))
        )

      self.block_5 = nn.Sequential(
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                         stride=(2, 2))
        )
      self.block_55 = nn.Sequential(
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.Conv2d(in_channels=512,
                      out_channels=512,
                      kernel_size=(3, 3),
                      stride=(1, 1),
                      padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(2, 2),
                          stride=(2, 2))
        )

    def forward(self, x):

        x = self.block_1(x)
        x = self.block_2(x)
        x = self.block_3(x)
        x = self.block_4(x)
        x = self.block_5(x)
        x = self.block_55(x)
        
        return x

### Depth Decoder

class DephDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        
        self.decd1  = decode_block(1024,512,4,1,0)
        self.decd2  = decode_block(512,512,4,2,1)
        self.decd3  = decode_block(512,256,4,2,1)
        self.decd4  = decode_block(256,128,4,2,1)
        self.decd5  = decode_block(128,128,4,2,1)
        self.decd6  = decode_block(128,64,3,1,1)
        self.decd7 = nn.Conv2d(64, 1, 1) 

    def forward(self, y1,y2):
      
        y0 = torch.cat([y1,y2],1)
        x = self.decd1(y0)
        x = self.decd2(x)
        x = self.decd3(x)
        x = self.decd4(x)
        x = self.decd5(x)
        x = self.decd6(x)
        x = self.decd7(x)
        return x

### MODEL

class AudioNet(nn.Module):
    def __init__(self):
        super().__init__()

        self.audio_encoder = SoundNet()
        self.image_encoder = VGG16(3)
        self.depth_decoder = DephDecoder()

    def forward(self, x1,x2,x_image):
        
        x = self.audio_encoder(x1,x2)
        y = self.image_encoder(x_image)
        depth = self.depth_decoder(x,y)
        return depth

with h5py.File('/content/drive/MyDrive/dataset_uint16_halfoverlap_plusuni2.h5', 'r') as hf:
    audio_first_train = hf['audio_first_train'][:]
    audio_second_train = hf['audio_second_train'][:]
    depth_train = hf['depth_train'][:]
    image_train = hf['image_train'][:]
    audio_first_val = hf['audio_first_val'][:]
    audio_second_val = hf['audio_second_val'][:]
    depth_val = hf['depth_val'][:]
    image_val = hf['image_val'][:]

class MyCustomDataset(Dataset):
    def __init__(self,  audio_folder_first, audio_folder_second, image, depth):
        self.audio_folder_first = audio_folder_first
        self.audio_folder_second = audio_folder_second
        self.image_folder = image
        self.depth_folder = depth
    def __getitem__(self, idx):
        image = self.image_folder[idx]
        depth = self.depth_folder[idx]

        # start_id = random.randint(0,20)
        first_channel = (self.audio_folder_first[idx])[200:2400]
        second_channel = (self.audio_folder_second[idx])[200:2400]
        # normalization audio data
        first_channel = first_channel/max(abs(first_channel))
        second_channel = second_channel/max(abs(second_channel))

        first_channel = np.expand_dims(np.expand_dims(np.array(first_channel, dtype=np.float32),axis=1),axis=0)
        second_channel = np.expand_dims(np.expand_dims(np.array(second_channel, dtype=np.float32),axis=1),axis=0)
        return torch.from_numpy(first_channel).float(),torch.from_numpy(second_channel).float(), torch.from_numpy(image).float(), torch.from_numpy(depth).float()
    def __len__(self):
        return len(self.depth_folder)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
n_GPU = torch.cuda.device_count()
print("{} {} device is used".format(n_GPU,device))
batch_size = 32
output_res = 128
learning_rate = 0.00005
epochs = 201
version = 0

custom_dataset = MyCustomDataset(audio_first_train, audio_second_train, image_train, depth_train)
val_dataset = MyCustomDataset(audio_first_val, audio_second_val, image_val, depth_val)
print("Number of train samples: {}".format(len(custom_dataset)))

# Define data loader
train_loader = DataLoader(dataset=custom_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
val_loader = DataLoader(dataset=val_dataset, batch_size=batch_size, shuffle=True, drop_last=True)
model = AudioNet()

model = model.float()
# if n_GPU > 1:
#     model = nn.DataParallel(model)
model.to(device)

criterion3 = nn.L1Loss(reduction='none')

optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.0001)

# if saved a pretrained model:
# checkpoint = torch.load("/content/drive/MyDrive/200vgguni_uncompletenet.pth")
# model.load_state_dict(checkpoint["state_dict"])
# optimizer.load_state_dict(checkpoint['optimizer'])
# checkpoint_epoch = checkpoint["epoch"]

# else:
checkpoint_epoch = 0

for param_group in optimizer.param_groups:
    print("Learning rate used: {}".format(param_group['lr']))

train_iter = 0
training_loss = []
validation_loss = []
training_loss2 = []
validation_loss2 = []
training_loss3 = []
validation_loss3 = []
training_abs_err = []
validation_abs_err = []
training_accuracy = []
validation_accuracy = []
training_histograms = []
validation_histograms = []

for epoch in range(checkpoint_epoch,epochs):
    print('* Epoch %d/%d' % (epoch, epochs))
    t0 = time.time()
    avg_loss3 = 0
    avg_val_loss3 = 0
    avg_acc3 = 0
    avg_val_acc3 = 0
    abs_err = 0
    abs_err_val = 0
    counter = 0

    # ------ TRAINING ---------
    model.train()  # train mode
    for i, (x1_batch, x2_batch, x_image, x_depth) in enumerate(train_loader):
      # cpu or cuda
      x1_batch = x1_batch.to(device)
      x2_batch = x2_batch.to(device)
      x_image = x_image.to(device)
      x_depth = x_depth.to(device)                     
      y1_batch = x1_batch.detach().clone()
      y2_batch = x2_batch.detach().clone()
      y_batch = torch.cat([y1_batch, y2_batch],1).to(device)
      # set parameter gradients to zero
      optimizer.zero_grad()
      # forward
      y_pred_depth = model(x1_batch,x2_batch,x_image)
      # loss
      loss3 = criterion3(y_pred_depth,x_depth)
      # no signal
      loss3 = loss3[x_depth!=0].mean()
      # backward
      loss3.backward()
      # optimizer update
      optimizer.step()
      # accuracy
      acc3 = ((1-torch.abs(y_pred_depth-x_depth))*100)
      acc3 = acc3.mean()
      # absolute error
      #for i in range(batch_size):
      y_plot = torch.squeeze(y_pred_depth, 0)*8000
      x_plot = torch.squeeze(x_depth, 0)*8000
      x_plot = x_plot.detach().cpu().numpy()
      y_plot = y_plot.detach().cpu().numpy()
      index_error = np.where(x_plot != 0)
      x_noerror = x_plot[index_error]
      y_noerror = y_plot[index_error]
      # absolute error mean (without no signal error)
      abs_err += np.abs(y_noerror-x_noerror).mean() / len(train_loader)
      # calculate metrics
      avg_loss3 += loss3 / len(train_loader)
      avg_acc3 += acc3 / len(train_loader)
      # plot metrics every epoch
      print('[{}/{}] - loss3: {:.4f} - acc3: {:.3f}'.format(i,len(train_loader)-1,loss3,acc3), end="\r",flush=True)
    training_loss3.append(avg_loss3.cpu().detach().numpy())
    training_accuracy.append(avg_acc3.cpu().detach().numpy())
    training_abs_err.append(abs_err)
    # plot of 10 samples at epoch 200
    if epoch == 200:
      for j in range(10):
        y_scaled = np.squeeze(y_plot[j],0)
        x_scaled = np.squeeze(x_plot[j],0)
        abs_err_matrix = np.abs(y_scaled-x_scaled)
        abs_err_matrix[np.where(x_scaled==0)]=0
        # violin plot
        sns.set_theme(style="whitegrid")
        sns.violinplot(x=abs_err_matrix.ravel(), split=True, inner="quart", linewidth=1, saturation=0.65)
        plt.title("Training absolute error violinplot")
        plt.show()
        # boxen plot
        sns.boxenplot(x=abs_err_matrix.ravel())
        plt.title("Training absolute error boxenplot")
        plt.xlabel("Absolute error")
        plt.ylabel("Pixel number")
        plt.show()
        # absolute error matrix
        sns.set_theme(style="white")
        sns.color_palette("mako", as_cmap=True)
        plt.imshow(abs_err_matrix)
        plt.colorbar()
        plt.title("Training absolute error")
        plt.show()
        # absolute error mean
        print("Absolute error average - training",abs_err_matrix.mean())
        # four plots in comparison
        titles = ['Training reconstruction','Training reconstruction colormap', 'Training ground truth', 'Training ground truth colormap']
        images = [y_scaled, y_scaled, x_scaled, x_scaled]
        plt.figure("Training results")
        for i in range(4):
          plt.subplot(2,2,i+1)
          if (i % 2) == 0: #even
            plt.imshow(images[i],cmap='gray')
          else:
            plt.imshow(images[i],cmap='jet')          
          plt.colorbar()
          plt.title(titles[i])
          plt.xticks([]),plt.yticks([])
        plt.show()
      
    # ------- VALIDATION ------------
    
    model.eval()  # validation mode

    with torch.no_grad():
    
        for x1_val, x2_val, x_image_val, x_depth_val in val_loader:
          x1_val = x1_val.to(device)
          x2_val = x2_val.to(device)
          x_image_val = x_image_val.to(device) 
          x_depth_val = x_depth_val.to(device)
          y1_val = x1_val.detach().clone()
          y2_val = x2_val.detach().clone()
          y_val = torch.cat([y1_val, y2_val],1)
          y_val = y_val.to(device)        
          # validation
          y_pred_depth_val = model(x1_val, x2_val, x_image_val)
          # loss
          loss_val3 = criterion3(y_pred_depth_val, x_depth_val)
          loss_val3 = loss_val3[x_depth_val!=0].mean()
          # accuracy
          acc_val3 = ((1-torch.abs(y_pred_depth_val-x_depth_val))*100)
          acc_val3 = acc_val3.mean()
          y_plot_val = torch.squeeze(y_pred_depth_val, 1)*8000
          x_plot_val = torch.squeeze(x_depth_val, 1)*8000
          y_plot_val = y_plot_val.detach().cpu().numpy()
          x_plot_val = x_plot_val.detach().cpu().numpy()
          index_error_val = np.where(x_plot_val != 0)
          x_noerror_val = x_plot_val[index_error_val]
          y_noerror_val = y_plot_val[index_error_val]
          # absolute error mean (without no signal error)
          abs_err_val += np.abs(y_noerror_val-x_noerror_val).mean() / len(val_loader)
          # calculate metrics2
          avg_val_loss3 += loss_val3 / len(val_loader)
          avg_val_acc3 += acc_val3 / len(val_loader)
          print('[{}/{}] - loss3: {:.4f} - acc3: {:.3f}'.format(i,len(val_loader)-1,loss_val3,acc_val3), end="\r",flush=True)
    validation_loss3.append(avg_val_loss3.cpu().detach().numpy())
    validation_abs_err.append(abs_err_val)
    if epoch == 200:
      for j in range(32):
        y_scaled_val = y_plot_val[j]
        x_scaled_val = x_plot_val[j]
        abs_err_val_matrix = np.abs(y_scaled_val-x_scaled_val)
        abs_err_val_matrix[np.where(x_scaled_val==0)]=0
        
        # violin plot
        sns.set_theme(style="whitegrid")
        sns.violinplot(x=abs_err_val_matrix.ravel(), split=True, inner="quart", linewidth=1, saturation=0.65)
        plt.title("Validation absolute error violinplot")
        plt.show()
        # boxen plot
        sns.boxenplot(x=abs_err_matrix.ravel())
        plt.title("Validation absolute error boxenplot")
        plt.show()
        # absolute error plot
        sns.set_theme(style="white") 
        sns.color_palette("mako", as_cmap=True)
        plt.imshow(abs_err_val_matrix)
        plt.show()
        
        plt.imshow(abs_err_val_matrix, cmap='gray')
        plt.colorbar()
        plt.title("Validation absolute error")
        plt.show()
        print("Absolute error average - validation",abs_err_val_matrix.mean())
        
        titles = ['Validation reconstruction','Validation reconstruction colormap', 'Validation ground truth', 'Validation ground truth colormap']
        images = [y_scaled_val, y_scaled_val, x_scaled_val, x_scaled_val]
        plt.figure("Validation results")
        for i in range(4):
          plt.subplot(2,2,i+1)
          if (i % 2) == 0:
            plt.imshow(images[i],cmap='gray')
          else:
            plt.imshow(images[i],cmap='jet')

          plt.colorbar()
          plt.title(titles[i])
          plt.xticks([]),plt.yticks([])
        plt.show()

        print('[{}/{}] - training loss: {:.4f} - validation loss: {:.4f}'.format(i,len(train_loader)-1, avg_loss3, avg_val_loss3), end="\r",flush=True)
        print("List of training loss per epoch - Depth:", training_loss3)        
        print("List of training absolute error average per epoch - Depth:", training_abs_err)
        print("List of validation absolute error average per epoch - Depth:", validation_abs_err)
    
    if epoch == 200:
      
      state = {
      'epoch': epoch,
      'state_dict': model.state_dict(),
      'optimizer': optimizer.state_dict()
      }
      torch.save(state, "/content/drive/MyDrive/200epoch_EC.pth")