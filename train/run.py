# -*- coding:utf-8 -*-

"""
    usage: python run.py --model bert --data intent
"""

import argparse
import importlib
import time

import numpy as np
import torch

try:
    from train.data_helper import build_dataset, build_iterator, get_time_dif
    from train.train_eval import train
    from utils import logger
except ImportError:
    from data_helper import build_dataset, build_iterator, get_time_dif
    from train_eval import train
    from utils import logger


def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def main(argv=None):
    parser = argparse.ArgumentParser(description='Train intent or reject classifier')
    parser.add_argument('--model', choices=('bert', 'bert_tiny'), required=True)
    parser.add_argument('--data', choices=('reject', 'intent'), required=True)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--learning-rate', type=float)
    parser.add_argument('--class-weighting', choices=('none', 'balanced'), default='none')
    args = parser.parse_args(argv)


    dataset = args.data  # 数据集
    model_name = args.model  # 模型
    try:
        x = importlib.import_module(f'train.models.{model_name}')
    except ImportError:
        x = importlib.import_module(f'models.{model_name}')
    config = x.Config(dataset)
    for name, value in (('num_epochs', args.epochs),
                        ('batch_size', args.batch_size),
                        ('learning_rate', args.learning_rate)):
        if value is not None:
            setattr(config, name, value)
    config.class_weighting = args.class_weighting
    config.seed = args.seed

    # 设置随机数种子
    set_seed(args.seed)

    start_time = time.time()
    logger.info("Loading data...")
    train_data, dev_data, test_data = build_dataset(config)
    train_iter = build_iterator(train_data, config, shuffle=True)
    dev_iter = build_iterator(dev_data, config)
    test_iter = build_iterator(test_data, config)
    time_dif = get_time_dif(start_time)
    logger.info(f"Time usage: {time_dif}")

    # train & eval
    model = x.Model(config).to(config.device)
    train(config, model, train_iter, dev_iter, test_iter)


if __name__ == '__main__':
    main()
