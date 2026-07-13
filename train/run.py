# -*- coding:utf-8 -*-

"""
    usage: python run.py --model bert --data intent
"""

import argparse
import importlib
import time
from pathlib import Path

import numpy as np
import torch

try:
    from train.artifacts import tagged_paths
    from train.data_helper import build_dataset, build_iterator, get_time_dif
    from train.train_eval import train
    from utils import logger
except ImportError:
    from artifacts import tagged_paths
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


def use_data_root(config, data_root):
    data_dir = Path(data_root).resolve() / config.dataset
    class_path = data_dir / 'class.txt'
    if not class_path.is_file():
        raise FileNotFoundError(f'class list not found: {class_path}')
    config.train_path = str(data_dir / 'train.txt')
    config.dev_path = str(data_dir / 'dev.txt')
    config.test_path = str(data_dir / 'test.txt')
    config.class_list = [line.strip() for line in class_path.read_text(encoding='utf-8').splitlines()]
    config.num_classes = len(config.class_list)


def use_run_tag(config, run_tag):
    config.save_path, config.metrics_path = tagged_paths(config.save_path, config.metrics_path, run_tag)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Train intent or reject classifier')
    parser.add_argument('--model', choices=('bert', 'bert_tiny'), required=True)
    parser.add_argument('--data', choices=('reject', 'intent'), required=True)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--learning-rate', type=float)
    parser.add_argument('--class-weighting', choices=('none', 'balanced'), default='none')
    parser.add_argument('--data-root', help='directory containing <dataset>/train.txt, dev.txt, and test.txt')
    parser.add_argument('--run-tag', help='save this experiment without overwriting the default checkpoint')
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
    if args.data_root:
        use_data_root(config, args.data_root)
    if args.run_tag:
        use_run_tag(config, args.run_tag)

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
