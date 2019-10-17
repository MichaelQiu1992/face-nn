#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: penghuailiang
# @Date  : 2019-10-04

from __future__ import division

import random
import scipy.misc
import util.logit as log
from lightcnn.extract_features import *
from ops import *
from faceparsing.evaluate import *


def random_params(cnt):
    """
    随机生成捏脸参数
    """
    params = []
    for i in range(cnt):
        params.append(random.randint(0, 1000) / 1000.0)
    return params


def param_2_arr(params):
    """
    捏脸参数转numpy array
    """
    cnt = len(params)
    array = np.array(params)
    array = array.reshape([1, 1, 1, cnt])
    return array


def to_gray(rgb):
    """
    灰度处理
    :param rgb: Tensor(RGB)
    :return: Tensor(Grey)
    """
    arr = np.mean(rgb, axis=2)
    return arr[:, :, np.newaxis]


def feature256(img, checkpoint):
    """
    使用light cnn提取256维特征参数
    :param checkpoint: lightcnn model
    :param img: tensor 输入图片 shape:(batch, 3, 512, 512)
    :return: 256维特征参数 tensor [batch, 256]
    """
    model = LightCNN_29Layers_v2(num_classes=80013)
    model.eval()
    model = torch.nn.DataParallel(model)  # .cuda()
    model.load_state_dict(checkpoint['state_dict'])
    transform = transforms.Compose([transforms.ToTensor()])
    batch = img.size(0)
    input = torch.zeros(1, 1, 128, 128)
    feature_tensor = torch.empty(batch, 256)
    for i in range(batch):
        _img = img[i].detach().numpy()
        _img = scipy.misc.imresize(arr=_img, size=(128, 128, 1), interp='bilinear')
        _img = to_gray(_img)
        _img = transform(_img)
        input[0, :, :, :] = _img
        input_var = torch.autograd.Variable(input, volatile=True)
        _, features = model(input_var)
        feature_tensor[i] = features
    return feature_tensor


def get_cos_distance(x1, x2):
    """
    calculate cos distance between two sets
    tensorflow: https://blog.csdn.net/liuchonge/article/details/70049413
    :param x1: [batch, 256] dimensions vector
    :param x2: [batch, 256 dimensions vector
    """
    batch = x1.size(0)
    result = torch.Tensor(batch)
    for i in range(batch):
        """
        # implement with tensorflow
        x1_norm = tf.sqrt(tf.reduce_sum(tf.square(x1)))
        x2_norm = tf.sqrt(tf.reduce_sum(tf.square(x2)))
        x1_x2 = tf.reduce_sum(tf.multiply(x1, x2))
        result[i] = x1_x2 / (x1_norm * x2_norm)
        """
        x1_norm = torch.sqrt(torch.sum(x1.mul(x1)))
        x2_norm = torch.sqrt(torch.sum(x2.mul(x2)))
        x1_x2 = torch.sum(x1.mul(x2))
        result[i] = x1_x2/(x1_norm * x2_norm)
    return result


def discriminative_loss(img1, img2, checkpoint):
    """
    论文里的判别损失
    Discriminative Loss
    :param checkpoint: lightcnn model
    :param img1: generated by engine, type: list of Tensor
    :param img2: generated by imitator, type: list of Tensor
    :return [batch, cos_distance]
    """
    print("image shape: ", img1.shape, img2.shape)
    x1 = feature256(img1, checkpoint)
    x2 = feature256(img2, checkpoint)
    print("feature shape: ", x1.shape, x2.shape)
    cos_t = get_cos_distance(x1, x2)
    return torch.ones(2) - cos_t


def evalute_face(img):
    """
    face segmentation model
    :return: face-parsing image
    """
    return out_evaluate(img)


def content_loss(img1, img2):
    """
    change resolution to 1/8, 512/8 = 64
    :return:
    """
    image1 = scipy.misc.imresize(arr=img1, size=(64, 64))
    image2 = scipy.misc.imresize(arr=img2, size=(64, 64))
    cross = tf.losses.softmax_cross_entropy(onehot_labels=image1, logits=image2, weights=0.2)
    return cross


def save_batch(input_painting_batch, input_photo_batch, output_painting_batch, output_photo_batch, filepath):
    """
    Concatenates, processes and stores batches as image 'filepath'.
    Args:
        input_painting_batch: numpy array of size [B x H x W x C]
        input_photo_batch: numpy array of size [B x H x W x C]
        output_painting_batch: numpy array of size [B x H x W x C]
        output_photo_batch: numpy array of size [B x H x W x C]
        filepath: full name with path of file that we save
    """

    def batch_to_img(batch):
        return np.reshape(batch, newshape=(batch.shape[0] * batch.shape[1], batch.shape[2], batch.shape[3]))

    inputs = np.concatenate([batch_to_img(input_painting_batch), batch_to_img(input_photo_batch)], axis=0)
    outputs = np.concatenate([batch_to_img(output_painting_batch), batch_to_img(output_photo_batch)], axis=0)
    to_save = np.concatenate([inputs, outputs], axis=1)
    to_save = np.clip(to_save, a_min=0., a_max=255.).astype(np.uint8)
    scipy.misc.imsave(filepath, arr=to_save)


def normalize_arr_of_imgs(arr):
    """
    Normalizes an array so that the result lies in [-1; 1].
    Args:
        arr: numpy array of arbitrary shape and dimensions.
    Returns:
    """
    return arr / 127.5 - 1.  # return (arr - np.mean(arr)) / np.std(arr)


def denormalize_arr_of_imgs(arr):
    """
    Inverse of the normalize_arr_of_imgs function.
    Args:
        arr: numpy array of arbitrary shape and dimensions.
    Returns:
    """
    return (arr + 1.) * 127.5
