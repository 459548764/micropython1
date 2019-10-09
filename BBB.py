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
import ot
tnum = 7

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
            torch.nn.Linear(64,10)
        )

    def forward(self,x):
        x = self.conv(x)
        x = x.view(-1,8*8*128)
        ft = self.feature(x)
        out = self.dense(ft)
        return ft,out

class OtLoss(torch.nn.Module):
    def __init__(self):
        super(OtLoss,self).__init__()

    def forward(self,src_feat,trg_ot):
        loss = 0.0
        for i, g in enumerate(src_feat):
            loss += torch.norm(src_feat[i] - trg_ot[i]) ** 2
        loss = loss / len(src_feat)
        return loss

def OtDist(batch_size,feat_dim,src_feat,trg_feat,src_label,trg_label):
    def get_dis(s,t,s_label,t_label):
        sum = 0.0
        for i in range(feat_dim):
            sum += (s[i] - t[i])**2
        dis = np.sqrt(sum)
        dis = dis * t_label[s_label]
        return dis

    trg_label = F.softmax(trg_label,dim=1)
    trg_label = trg_label.data.cpu().numpy()

    src_feat = src_feat.data.cpu().numpy()
    trg_feat = trg_feat.data.cpu().numpy()

    dist = np.zeros([batch_size,batch_size])
    for i in range(batch_size):
        for j in range(batch_size):
            dist[i][j] = get_dis(src_feat[i],trg_feat[i],src_label[i],trg_label[i])
    return dist

def guassian_kernel(source, target, kernel_mul=2.0, kernel_num=5, fix_sigma=None):
    n_samples = int(source.size()[0])+int(target.size()[0])
    total = torch.cat([source, target], dim=0)
    total0 = total.unsqueeze(0).expand(int(total.size(0)), int(total.size(0)), int(total.size(1)))
    total1 = total.unsqueeze(1).expand(int(total.size(0)), int(total.size(0)), int(total.size(1)))
    L2_distance = ((total0-total1)**2).sum(2)
    if fix_sigma:
        bandwidth = fix_sigma
    else:
        bandwidth = torch.sum(L2_distance.data) / (n_samples**2-n_samples)
    bandwidth /= kernel_mul ** (kernel_num // 2)
    bandwidth_list = [bandwidth * (kernel_mul**i) for i in range(kernel_num)]
    kernel_val = [torch.exp(-L2_distance / bandwidth_temp) for bandwidth_temp in bandwidth_list]
    return sum(kernel_val)

def mmd_rbf(source, target, kernel_mul=2.0, kernel_num=5, fix_sigma=None):
    batch_size = int(source.size()[0])
    kernels = guassian_kernel(source, target,
                              kernel_mul=kernel_mul, kernel_num=kernel_num, fix_sigma=fix_sigma)
    XX = kernels[:batch_size, :batch_size]
    YY = kernels[batch_size:, batch_size:]
    XY = kernels[:batch_size, batch_size:]
    YX = kernels[batch_size:, :batch_size]
    loss = torch.mean(XX + YY - XY -YX)
    return loss

def torch_pack(input,state = False):
    input = torch.from_numpy(input)
    if state == False:
        input = input.type(torch.FloatTensor)
    else:
        input = input.type(torch.LongTensor)
    input = input.cuda()
    return input

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
lenet = LENET().to(device)

class_cost = torch.nn.CrossEntropyLoss()
ot_cost = OtLoss()
optimizer = torch.optim.Adam(lenet.parameters())

batch_size = 128
mnist_img,mnist_label = load_USPS('usps')
usps_img,usps_label = load_mnist('mnist')
nclass = 10
n_epoch = 1000000

for epoch in range(1,20000):
    base_sample = 5000
    test_sample = 2000
    src_acc = 0
    trg_acc = 0

    src_idx = epoch % int(mnist_img.shape[0]/batch_size)
    trg_idx = epoch % int(usps_img.shape[0]/batch_size)
    src_img = mnist_img[src_idx*batch_size:(src_idx+1)*batch_size]
    src_label = mnist_label[src_idx*batch_size:(src_idx+1)*batch_size]
    trg_img = usps_img[trg_idx*batch_size:(trg_idx+1)*batch_size]
    trg_label = usps_label[trg_idx*batch_size:(trg_idx+1)*batch_size]

    src_img = Variable(torch_pack(src_img))
    trg_img = Variable(torch_pack(trg_img))
    src_labels = Variable(torch_pack(src_label,True))

    src_feat,src_output = lenet(src_img)
    trg_feat,trg_output = lenet(trg_img)
    src_feats = src_feat.data.cpu().numpy()

    optimizer.zero_grad()
    class_loss = class_cost(src_output,src_labels)
    c = OtDist(batch_size,64,src_feat,trg_feat,src_label,trg_output)
    g = ot.emd(ot.unif(batch_size),ot.unif(batch_size),c)
    xst = batch_size * g.dot(src_feats)
    xst = Variable(torch_pack(xst))
    ot_loss = mmd_rbf(trg_feat,xst)
    loss = class_loss + 0.0 * ot_loss
    
    if epoch % 1 == 0:
        print('-------')
        print('loss: ',loss)
        print('class_loss: ',class_loss)
        print('ot_loss: ',ot_loss)
        print('-------')
    loss.backward()
    optimizer.step()

    if epoch % 100 == 0:
        print(epoch)
        print('<Testing>')
        test_img = usps_img[0:test_sample]
        test_label = usps_label[0:test_sample]
        test_img = torch_pack(test_img)
        test_label = torch_pack(test_label,True)
        feature,output = lenet(test_img)

        feature = feature.data.cpu().numpy()
        output = output.data.cpu().numpy()
        hard_output = np.argmax(output,axis=1)
        for i in range(test_sample):
            if(hard_output[i] == usps_label[i]):
                trg_acc += 1
        trg_acc /= test_sample
        print('trg_acc: ',trg_acc)
        print('<Testing OVER>')


