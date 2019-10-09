import numpy as np
import pylab as pl
import torch
from torch.autograd import Variable
import ot

x_samples = 10000
x_radius = 0.01
x_var = 0.01
x_train = np.zeros((x_samples,2))
r = np.random.normal(x_radius,x_var,x_samples)
theta = np.random.rand(x_samples)*2*np.pi
x_train[:,0] = r*np.cos(theta)
x_train[:,1] = r*np.sin(theta)

y_samples = 10000
y_radius = 0.3
y_var = 0.005
y_train = np.zeros((y_samples,2))
r = np.random.normal(y_radius,y_var,y_samples)
theta = np.random.rand(y_samples)*2*np.pi
y_train[:,0] = r*np.cos(theta)
y_train[:,1] = r*np.sin(theta)

class GENERATOR(torch.nn.Module):
    def __init__(self):
        super(GENERATOR,self).__init__()
        self.dense = torch.nn.Sequential(
            torch.nn.Linear(2,128),
            torch.nn.ReLU(),
            torch.nn.Linear(128,64),
            torch.nn.ReLU(),
            torch.nn.Linear(64,2)
        )

    def forward(self,x):
        x = self.dense(x)
        return x

class DISCRIMINATOR(torch.nn.Module):
    def __init__(self):
        super(DISCRIMINATOR,self).__init__()
        self.feature = torch.nn.Sequential(
            torch.nn.Linear(2,128),
            torch.nn.ReLU(),
            torch.nn.Linear(128,64),
            torch.nn.ReLU()
        )

        self.dense = torch.nn.Sequential(
            torch.nn.Linear(64,2)
        )

    def forward(self,x):
        ft = self.feature(x)
        out = self.dense(ft)
        return ft,out

class CenterLoss(torch.nn.Module):
    def __init__(self):
        super(CenterLoss,self).__init__()

    def forward(self,x,centers):
        loss = 0.0
        for i, g in enumerate(x):
            loss += torch.norm(x[i] - centers) ** 2
        loss = loss / len(x)
        return loss

class OtLoss(torch.nn.Module):
    def __init__(self):
        super(OtLoss,self).__init__()

    def forward(self,src_feat,trg_ot):
        loss = 0.0
        for i, g in enumerate(src_feat):
            loss += torch.norm(src_feat[i] - trg_ot[i]) ** 2
        loss = loss / len(src_feat)
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
generator = GENERATOR().to(device)
discriminator = DISCRIMINATOR().to(device)

domain_cost = torch.nn.CrossEntropyLoss()
center_cost = CenterLoss()
optimizer_d = torch.optim.Adam(discriminator.parameters())
batch_size = 128

for epoch in range(1,10000):
    optimizer_d.zero_grad()

    src_idx = epoch % int(x_train.shape[0]/batch_size)
    trg_idx = epoch % int(y_train.shape[0]/batch_size)
    src_img = x_train[src_idx*batch_size:(src_idx+1)*batch_size]
    trg_img = y_train[trg_idx*batch_size:(trg_idx+1)*batch_size]
    labels = np.ones(batch_size*2)
    for i in range(batch_size):
        labels[i] = 0

    src_img = Variable(torch_pack(src_img))
    trg_img = Variable(torch_pack(trg_img))
    domain_label = Variable(torch_pack(labels,True))

    src_img = generator(src_img).detach()
    src_feat,src_output = discriminator(src_img)
    trg_feat,trg_output = discriminator(trg_img)
    output = torch.cat([src_output,trg_output],dim=0)

    np_src_feat = src_feat.data.cpu().numpy()
    np_trg_feat = trg_feat.data.cpu().numpy()
    src_center = np.mean(np_src_feat,axis=0)
    trg_center = np.mean(np_trg_feat,axis=0)
    src_center = Variable(torch_pack(src_center))
    trg_center = Variable(torch_pack(trg_center))

    class_loss = domain_cost(output,domain_label)
    src_loss = center_cost(src_feat,src_center)
    trg_loss = center_cost(trg_feat,trg_center)
    loss = class_loss + 0.0 *(src_loss + trg_loss)
    if epoch % 100 == 0:
        print('-------',epoch)
        print('loss: ',loss)
        print('src_loss: ',src_loss)
        print('trg_loss: ',trg_loss)
        print('-------')
    loss.backward()
    optimizer_d.step()

print('NEW STAGE')
for k,v in discriminator.named_parameters():
    v.requires_grad = False

src_img = x_train[0:2000]
trg_img = y_train[0:2000]
src_img = torch_pack(src_img)
trg_img = torch_pack(trg_img)
src_feat,_ = discriminator(src_img)
trg_feat,_ = discriminator(trg_img)
src_feat = src_feat.data.cpu().numpy()
trg_feat = trg_feat.data.cpu().numpy()
src_center = np.mean(src_feat,axis=0)
trg_center = np.mean(trg_feat,axis=0)
trg_center = Variable(torch_pack(trg_center))

ot_cost = OtLoss()
optimizer_g = torch.optim.Adam(generator.parameters())
for epoch in range(1,100000):
    optimizer_g.zero_grad()

    src_idx = epoch % int(x_train.shape[0]/batch_size)
    trg_idx = epoch % int(y_train.shape[0]/batch_size)
    src_img = x_train[src_idx*batch_size:(src_idx+1)*batch_size]
    trg_img = y_train[trg_idx*batch_size:(trg_idx+1)*batch_size]
    labels = np.ones(batch_size)

    src_img = Variable(torch_pack(src_img))
    trg_img = Variable(torch_pack(trg_img))
    domain_label = Variable(torch_pack(labels,True))

    fake_trg = generator(src_img)
    fake_feat,fake_output = discriminator(fake_trg)
    trg_feat,trg_output = discriminator(trg_img)

    np_fake_feat = fake_feat.data.cpu().numpy()
    np_trg_feat = trg_feat.data.cpu().numpy()
    c = ot.dist(np_fake_feat,np_trg_feat)
    g = ot.emd(ot.unif(batch_size),ot.unif(batch_size),c)
    xst = batch_size * g.dot(np_trg_feat)
    xst = Variable(torch_pack(xst))

    ot_loss = ot_cost(fake_feat,xst)
    if epoch % 100 == 0:
        print(fake_trg)
        print('-------',epoch)
        print('loss: ',ot_loss)
        print('-------')
    ot_loss.backward()
    optimizer_g.step()
