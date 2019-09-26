# -*- coding:utf-8 -*-
###
# File: main.py
# Created Date: Sunday, September 15th 2019, 12:28:36 pm
# Author: yusnows
# -----
# Last Modified:
# Modified By:
# -----
# Copyright (c) 2019 yusnows
#
# All shall be well and all shall be well and all manner of things shall be well.
# Nope...we're doomed!
# -----
# HISTORY:
# Date      	By	Comments
# ----------	---	----------------------------------------------------------
###
import os
import json
import time
import config
import classifi_model as cmodel
import csv_dataset as csvdset
from efficientnet_pytorch import EfficientNet
import torch
import torchvision.transforms as transforms
import PIL


if __name__ == "__main__":
    conf = config.Config()
    opt = conf.create_opt()
    print(opt)
    # 保存opt, 便于复现实验结果
    os.makedirs(opt.opt_save_dir, exist_ok=True)
    with open(os.path.join(opt.opt_save_dir, 'opt.json'), 'w') as f:
        json.dump(opt.__dict__, f)
    # -------------------------------------------------------------------------
    # 交叉验证
    # -------------------------------------------------------------------------
    # 准备交叉验证的.csv文件
    if opt.fold_begin == 0:
        train_csvs, valid_csvs = csvdset.generate_k_fold_seq(opt.traincsv, opt.fold_out, opt.fold_num)
    else:
        train_csvs, valid_csvs = [], []
        for i in range(opt.fold_num):
            train_csvs.append(os.path.join(opt.fold_out, "%d/trian_%d.csv" % (i, i)))
            valid_csvs.append(os.path.join(opt.fold_out, "%d/valid_%d.csv" % (i, i)))
    if 'efficiennet' in opt.arch:
        image_size = EfficientNet.get_image_size(opt.arch)
    else:
        print('not efficientnet image size')
        image_size = opt.imageSize
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.4, 1.0), interpolation=PIL.Image.BICUBIC),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        normalize,
    ])
    score_list, acc_list = [], []
    for fold_idx in range(opt.fold_begin, opt.fold_num):
        print("training on %d fold" % fold_idx)
        trian_csv = train_csvs[fold_idx]
        valid_csv = valid_csvs[fold_idx]
        train_dataset = csvdset.CsvDataset(trian_csv, opt.trainroot, transform=train_transforms)
        valid_dataset = csvdset.CsvDataset(valid_csv, opt.trainroot, transform=train_transforms)
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=opt.batchSize, shuffle=True, num_workers=opt.workers, drop_last=True,
            pin_memory=False)
        valid_loader = torch.utils.data.DataLoader(
            valid_dataset, batch_size=opt.batchSize, shuffle=False, num_workers=opt.workers, drop_last=False,
            pin_memory=False)
        classi_model = cmodel.ClassiModel(
            arch=opt.arch, gpus=[opt.gpu], optimv=opt.optimizer, num_classes=opt.num_classes,
            lr=opt.lr_list[0], weight_decay=opt.weight_decay, from_pretrained=opt.from_pretrained)
        avg_valid_acc, avg_valid_score = classi_model.train_fold(train_loader, valid_loader, fold_idx, opt)
        acc_list.append(avg_valid_acc)
        score_list.append(avg_valid_score)

    # 打印在验证集上的平均准确率
    print('total accuracy:', sum(acc_list) / opt.fold_num)
    print('total score:', sum(score_list) / opt.fold_num)
