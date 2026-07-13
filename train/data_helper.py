# -*- coding:utf-8 -*-

import math
import random
import time
from datetime import timedelta

import torch
from tqdm import tqdm


PAD, CLS = '[PAD]', '[CLS]'  # padding符号, bert中综合信息符号


def build_dataset(config):

    def load_dataset(path, pad_size=32):
        contents = []
        with open(path, 'r', encoding='UTF-8') as f:
            for line_no, line in enumerate(tqdm(f), 1):
                lin = line.strip()
                if not lin:
                    continue
                parts = lin.split('\t')
                if len(parts) < 2:
                    raise ValueError(f'{path}:{line_no}: expected text and label')
                content = '\t'.join(parts[:-1]).strip()
                try:
                    label = int(parts[-1].strip())
                except ValueError as exc:
                    raise ValueError(f'{path}:{line_no}: invalid label') from exc
                token_ids, seq_len, mask = encode_text(config, content, pad_size)
                contents.append((token_ids, label, seq_len, mask))
        return contents
    train = load_dataset(config.train_path, config.pad_size)
    dev = load_dataset(config.dev_path, config.pad_size)
    test = load_dataset(config.test_path, config.pad_size)
    return train, dev, test


def encode_text(config, text, pad_size=None):
    """Tokenize one query with exactly the same rules used during training."""
    text = str(text or '').strip()
    if not text:
        raise ValueError('text must not be empty')
    pad_size = pad_size or config.pad_size
    tokens = [CLS] + config.tokenizer.tokenize(text)
    token_ids = config.tokenizer.convert_tokens_to_ids(tokens)
    seq_len = min(len(token_ids), pad_size)
    token_ids = token_ids[:pad_size]
    mask = [1] * seq_len + [0] * (pad_size - seq_len)
    token_ids += [0] * (pad_size - len(token_ids))
    return token_ids, seq_len, mask


class DatasetIterater(object):
    def __init__(self, batches, batch_size, device, shuffle=False):
        if not batches:
            raise ValueError('dataset must contain at least one valid sample')
        if batch_size < 1:
            raise ValueError('batch_size must be positive')
        self.batch_size = batch_size
        self.batches = list(batches)
        self.shuffle = shuffle
        self.n_batches = math.ceil(len(self.batches) / batch_size)
        self.index = 0
        self.device = device

    def _to_tensor(self, datas):
        x = torch.LongTensor([_[0] for _ in datas]).to(self.device)
        y = torch.LongTensor([_[1] for _ in datas]).to(self.device)

        # pad前的长度(超过pad_size的设为pad_size)
        seq_len = torch.LongTensor([_[2] for _ in datas]).to(self.device)
        mask = torch.LongTensor([_[3] for _ in datas]).to(self.device)
        return (x, seq_len, mask), y

    def __next__(self):
        if self.index >= self.n_batches:
            self.index = 0
            raise StopIteration
        start = self.index * self.batch_size
        batches = self.batches[start: start + self.batch_size]
        self.index += 1
        return self._to_tensor(batches)

    def __iter__(self):
        if self.index == 0 and self.shuffle:
            random.shuffle(self.batches)
        return self

    def __len__(self):
        return self.n_batches


def build_iterator(dataset, config, shuffle=False):
    return DatasetIterater(dataset, config.batch_size, config.device, shuffle=shuffle)


def get_time_dif(start_time):
    """获取已使用时间"""
    end_time = time.time()
    time_dif = end_time - start_time
    return timedelta(seconds=int(round(time_dif)))
