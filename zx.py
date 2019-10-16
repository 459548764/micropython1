import itertools
import ot
import scipy.io
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import matplotlib as mpl
import torch
import torch.nn.functional as F
import os
import pickle
import numpy as np
from torch.autograd import Variable
import cv2
import random

def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    torch.backends.cudnn.deterministic = True

# 设置随机数种子
setup_seed(20)

def load_mnistm(image_dir,split='train'):
    print('Loading mnistm dataset.')
    image_file='mnistm_train.pkl' if split=='train' else 'mnistm_test.pkl'
    image_dir=os.path.join(image_dir,image_file)
    with open(image_dir, 'rb') as f:
        mnistm = pickle.load(f,encoding='iso-8859-1')
    images = mnistm['data']

    img_num = images.shape[0]
    img_repo = np.zeros([img_num,32,32,1])
    for i in range(img_num):
        for m in range(32):
            for n in range(32):
                img_repo[i][m][n][0] = 0.299*images[i][m][n][0] + 0.587*images[i][m][n][1] + 0.114*images[i][m][n][2]
    images = np.reshape(img_repo,[-1,1,32,32])

    labels = mnistm['label']
    labels=np.squeeze(labels).astype(int)
    return images,labels

def load_svhn(image_dir, split='train'):
    print ('Loading SVHN dataset.')

    image_file = 'train_32x32.mat' if split == 'train' else 'test_32x32.mat'

    image_dir = os.path.join(image_dir, image_file)
    svhn = scipy.io.loadmat(image_dir)
    images = np.transpose(svhn['X'], [3, 0, 1, 2]) / 127.5 - 1

    img_num = images.shape[0]
    img_repo = np.zeros([img_num,32,32,1])
    for i in range(img_num):
        for m in range(32):
            for n in range(32):
                img_repo[i][m][n][0] = 0.299*images[i][m][n][0] + 0.587*images[i][m][n][1] + 0.114*images[i][m][n][2]
    images = np.reshape(img_repo,[-1,1,32,32])

    labels = svhn['y'].reshape(-1)
    labels[np.where(labels == 10)] = 0
    #domain_tag = np.zeros(images.shape[0])
    return images, labels

def load_mnist(image_dir, split='train'):
    print ('Loading MNIST dataset.')

    image_file = 'train.pkl' if split == 'train' else 'test.pkl'
    image_dir = os.path.join(image_dir, image_file)
    with open(image_dir, 'rb') as f:
        mnist = pickle.load(f)
    images = mnist['X'] / 127.5 - 1
    images = np.reshape(images,[-1,1,32,32])
    labels = mnist['y']
    labels = np.squeeze(labels).astype(int)
    return images,labels

def load_USPS(image_dir,split='train'):
    print('Loading USPS dataset.')
    image_file='USPS_train.pkl' if split=='train' else 'USPS_test.pkl'
    image_dir=os.path.join(image_dir,image_file)
    with open(image_dir, 'rb') as f:
        usps = pickle.load(f,encoding='iso-8859-1')
    images = usps['data']
    images=np.reshape(images,[-1,1,32,32])
    labels = usps['label']
    labels=np.squeeze(labels).astype(int)
    return images,labels

class ENCODER(torch.nn.Module):
    def __init__(self):
        super(ENCODER,self).__init__()

        self.conv = torch.nn.Sequential(
            torch.nn.Conv2d(1,32,kernel_size=3,stride=1,padding=1),
            torch.nn.LeakyReLU(),
            torch.nn.InstanceNorm2d(32,affine=True),
            torch.nn.MaxPool2d(2,2),

            torch.nn.Conv2d(32,64,kernel_size=3,stride=1,padding=1),
            torch.nn.LeakyReLU(),
            torch.nn.InstanceNorm2d(64,affine=True),
            torch.nn.MaxPool2d(2,2),

            torch.nn.Conv2d(64,128,kernel_size=3,stride=1,padding=1),
            torch.nn.LeakyReLU(),
            torch.nn.InstanceNorm2d(128,affine=True),
            torch.nn.MaxPool2d(2,2)
        )

        self.dense = torch.nn.Sequential(
            torch.nn.Linear(4*4*128,4*128)
        )

    def forward(self,x):
        x = self.conv(x)
        x = x.view(-1,4*4*128)
        x = self.dense(x)
        eps = Variable(torch.randn(x.size(0),4*128)).cuda()
        x = x + eps
        return x

class DECODER(torch.nn.Module):
    def __init__(self):
        super(DECODER,self).__init__()

        self.dense = torch.nn.Sequential(
            torch.nn.Linear(4*128,4*4*128),
            torch.nn.BatchNorm1d(4*4*128)
        )

        self.deconv = torch.nn.Sequential(
            torch.nn.ConvTranspose2d(128,64,kernel_size=4,stride=2,padding=1),
            torch.nn.LeakyReLU(),
            torch.nn.InstanceNorm2d(64,affine=True),

            torch.nn.ConvTranspose2d(64,32,kernel_size=4,stride=2,padding=1),
            torch.nn.LeakyReLU(),
            torch.nn.InstanceNorm2d(32,affine=True),

            torch.nn.ConvTranspose2d(32,1,kernel_size=4,stride=2,padding=1),
            torch.nn.Tanh()
        )

    def forward(self,x):
        x = self.dense(x)
        x = x.view(-1,128,4,4)
        x = self.deconv(x)
        return x

class LENET(torch.nn.Module):
    def __init__(self):
        super(LENET,self).__init__()

        self.conv = torch.nn.Sequential(
            torch.nn.Conv2d(1,64,kernel_size=5,stride=1,padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(stride=2,kernel_size=2),
            torch.nn.Conv2d(64,128,kernel_size=5,stride=1,padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(stride=2,kernel_size=2)
        )

        self.feature = torch.nn.Sequential(
            torch.nn.Linear(128*8*8,1024),
            torch.nn.ReLU(),
            torch.nn.Linear(1024,64),
            torch.nn.ReLU()
        )

        self.dense = torch.nn.Sequential(
            torch.nn.Linear(64,2)
        )

    def forward(self,x):
        x = self.conv(x)
        x = x.view(-1,8*8*128)
        ft = self.feature(x)
        out = self.dense(ft)
        return ft,out

def torch_pack(input,state = False):
    input = torch.from_numpy(input)
    if state == False:
        input = input.type(torch.FloatTensor)
    else:
        input = input.type(torch.LongTensor)
    input = input.cuda()
    return input


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
encoder = ENCODER().to(device)
decoder = DECODER().to(device)
lenet = LENET().to(device)

class_cost = torch.nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(lenet.parameters())

batch_size = 128
mnist_img,mnist_label = load_mnist('mnist')
nclass = 10
n_epoch = 1000000

for epoch in range(1,1000):
    centers = np.zeros([10,64])
    base_sample = 5000
    test_sample = 2000
    src_acc = 0
    trg_acc = 0

    labels = np.ones(batch_size*2)
    for i in range(batch_size):
        labels[i] = 0

    src_idx = epoch % int(mnist_img.shape[0]/batch_size)
    src_img = mnist_img[src_idx*batch_size:(src_idx+1)*batch_size]
    src_label = mnist_label[src_idx*batch_size:(src_idx+1)*batch_size]

    src_img = Variable(torch_pack(src_img))
    src_label = Variable(torch_pack(src_label,True))
    domain_label = Variable(torch_pack(labels,True))

    src_enc = encoder(src_img).detach()
    src_dec = decoder(src_enc).detach()

    src_feat,src_output = lenet(src_img)
    fake_feat,fake_output = lenet(src_dec)
    output = torch.cat([src_output,fake_output],dim=0)

    optimizer.zero_grad()
    class_loss = class_cost(output,domain_label)
    loss = class_loss
    if epoch % 100 == 0:
        print('-------')
        print('loss: ',loss)
        print('class_loss: ',class_loss)
        print('-------')

    loss.backward()
    optimizer.step()


print('NEW STAGE')
for k,v in lenet.named_parameters():
    v.requires_grad = False

ot_cost = torch.nn.MSELoss()
rec_cost = torch.nn.MSELoss()
optimizer_rec = torch.optim.Adam(itertools.chain(
    encoder.parameters(),
    decoder.parameters()
))

mean = np.zeros(4*128)
cov = np.zeros([4*128,4*128])
for i in range(4*128):
    cov[i][i] = 1

for epoch in range(1,1000000000):
    optimizer_rec.zero_grad()

    x = np.random.multivariate_normal(mean,cov,(batch_size),'raise')

    src_idx = epoch % int(mnist_img.shape[0]/batch_size)
    src_img = mnist_img[src_idx*batch_size:(src_idx+1)*batch_size]

    src_img = Variable(torch_pack(src_img))
    src_enc = encoder(src_img)
    src_dec = decoder(src_enc)

    src_ft,_ = lenet(src_img)
    src_fake_ft,_ = lenet(src_dec)

    src_enc_numpy = src_enc.data.cpu().numpy()
    c = ot.dist(src_enc_numpy,x)
    g = ot.emd(ot.unif(batch_size),ot.unif(batch_size),c)
    xst = batch_size * g.dot(x)
    xst = Variable(torch_pack(xst))

    dis_src_ft = src_ft.data.cpu().numpy()
    dis_src_fake_ft = src_fake_ft.data.cpu().numpy()

    c = ot.dist(dis_src_ft,dis_src_fake_ft)
    g = ot.emd(ot.unif(batch_size),ot.unif(batch_size),c)
    dis_xst = batch_size * g.dot(dis_src_ft)
    dis_xst = Variable(torch_pack(dis_xst))

    src_rec_loss = rec_cost(src_dec,src_img)
    ot_loss = ot_cost(src_enc,xst)
    dis_loss = ot_cost(src_fake_ft,dis_xst)
    rec_loss = 1*src_rec_loss + 0.01*(ot_loss + dis_loss)
    rec_loss.backward()
    optimizer_rec.step()

    if epoch % 100 == 0:
        print('-------',epoch)
        print('rec_loss: ',rec_loss)
        print('ot_loss: ',ot_loss)
        print('dis_loss: ',dis_loss)
        print('-------')
