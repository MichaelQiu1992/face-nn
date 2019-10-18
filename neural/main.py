#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: penghuailiang
# @Date  : 2019-09-20


import utils
from imitator import Imitator
from feature_extractor import FeatureExtractor
from net import Net
from parse import parser
import logging
import torch
import util.logit as log


def ex_net():
    """
    建立和引擎的通信
    python中启动之后， unity菜单栏选中Tools->Connect
    :return:
    """
    net = Net(5010, 5011)
    while True:
        r_input = input("command: \n")
        if r_input == "s":
            msg = input("input: ")
            net.only_send(msg)
        elif r_input == 'r':
            msg = input("input: ")
            net.send_recv(msg)
        elif r_input == "q":
            net.only_send("quit")
            net.close()
            break
        else:
            log.error("unknown code, quit")
            net.close()
            break


if __name__ == '__main__':
    args = parser.parse_args()
    log.init("FaceNeural", logging.DEBUG, log_path="output/log.txt")

    if args.phase == "train_imitator":
        log.info('imitator train mode')
        imitator = Imitator("neural imitator", args)
        imitator.batch_train()
    elif args.phase == "train_extractor":
        log.info('feature extractor train mode')
        extractor = FeatureExtractor("neural extractor", args)
        extractor.batch_train()
    elif args.phase == "inference_imitator":
        log.info("inference imitator")
        imitator = Imitator("neural imitator", args)
        imitator.load_checkpoint("./output/imitator/")
    elif args.phase == "lightcnn":
        log.info("light cnn test")
        checkpoint = torch.load("./dat/LightCNN_29Layers_V2_checkpoint.pth.tar", map_location="cpu")
        img = torch.randn(1, 3, 512, 512)
        features = utils.feature256(img, checkpoint)
        log.info(features.size())
    elif args.phase == "faceparsing":
        log.info("faceparsing")
    elif args.phase == "net":
        log.info("net start with ports (%d, %d)", 5010, 5011)
        ex_net()