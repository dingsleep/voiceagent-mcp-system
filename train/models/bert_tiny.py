# -*- coding:utf-8 -*-

import torch
import torch.nn as nn
from pathlib import Path

try:
    from train.core import BertModel, BertTokenizer
except ImportError:
    from core import BertModel, BertTokenizer


class Config(object):

    """配置参数"""
    def __init__(self, dataset):
        root = Path(__file__).resolve().parents[2]
        self.dataset = dataset
        self.model_name = 'bert_tiny'
        data_dir = root / 'train' / 'data' / dataset
        self.train_path = str(data_dir / 'train.txt')
        self.dev_path = str(data_dir / 'dev.txt')
        self.test_path = str(data_dir / 'test.txt')
        self.class_list = [x.strip() for x in (data_dir / 'class.txt').read_text(encoding='utf-8').splitlines()]
        self.save_path = str(root / 'train' / 'saved' / dataset / (self.model_name + '.ckpt'))
        self.metrics_path = str(root / 'train' / 'saved' / dataset / (self.model_name + '.metrics.json'))
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')     # GPU

        self.require_improvement = 1000                                 # 若超过1000batch效果还没提升，则提前结束训练
        self.eval_interval = 100
        self.max_grad_norm = 1.0
        self.num_classes = len(self.class_list)                         # 类别数
        self.num_epochs = 3                                             # epoch数
        self.batch_size = 128                                           # mini-batch大小
        self.pad_size = 32                                              # 每句话处理成的长度(短填长切)
        self.learning_rate = 5e-5                                       # 学习率
        self.bert_path = str(root / 'train' / 'pretrained' / 'roberta_tiny_clue')
        self.tokenizer = BertTokenizer.from_pretrained(self.bert_path)  # 加载tokenizer
        self.hidden_size = 312                                          # 隐藏层维度


class Model(nn.Module):

    def __init__(self, config):
        super(Model, self).__init__()
        self.bert = BertModel.from_pretrained(config.bert_path)
        for param in self.bert.parameters():
            param.requires_grad = True
        self.fc = nn.Linear(config.hidden_size, config.num_classes)

    def forward(self, x):
        context = x[0]  # 输入的句子
        mask = x[2]  # 对padding部分进行mask，和句子一个size，padding部分用0表示，如：[1, 1, 1, 1, 0, 0]
        _, pooled = self.bert(context, attention_mask=mask, output_all_encoded_layers=False)
        out = self.fc(pooled)
        return out
