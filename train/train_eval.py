# -*- coding:utf-8 -*-

import json

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn import metrics
import time
from pathlib import Path

try:
    from train.data_helper import get_time_dif
    from train.core.optimization import BertAdam
except ImportError:
    from data_helper import get_time_dif
    from core.optimization import BertAdam
from utils import logger


def build_class_weights(config, train_iter):
    if getattr(config, 'class_weighting', 'none') != 'balanced':
        return None
    counts = np.bincount(
        [row[1] for row in train_iter.batches],
        minlength=config.num_classes,
    ).astype(np.float64)
    present = counts > 0
    weights = np.zeros(config.num_classes, dtype=np.float32)
    weights[present] = counts.sum() / (present.sum() * counts[present])
    return torch.tensor(weights, dtype=torch.float32, device=config.device)


def find_best_threshold(labels, positive_probs):
    """Choose the reject threshold that maximizes macro F1 on validation data."""
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], positive_probs)))
    best_threshold, best_f1 = 0.5, -1.0
    for threshold in candidates:
        predictions = (positive_probs >= threshold).astype(int)
        score = metrics.f1_score(labels, predictions, average='macro', zero_division=0)
        if score > best_f1 or (score == best_f1 and abs(threshold - 0.5) < abs(best_threshold - 0.5)):
            best_threshold, best_f1 = float(threshold), float(score)
    return best_threshold


def _collect_predictions(config, model, data_iter, class_weights=None):
    model.eval()
    loss_total = 0.0
    labels_all = []
    probs_all = []
    with torch.no_grad():
        for texts, labels in data_iter:
            outputs = model(texts)
            loss_total += F.cross_entropy(outputs, labels, weight=class_weights).item()
            labels_all.extend(labels.detach().cpu().numpy().tolist())
            probs_all.extend(F.softmax(outputs, dim=-1).cpu().numpy().tolist())
    return np.asarray(labels_all, dtype=int), np.asarray(probs_all), loss_total / len(data_iter)


def _classification_metrics(config, labels_all, probs_all, threshold=None):
    if threshold is not None and config.dataset == 'reject':
        predict_all = (probs_all[:, 1] >= threshold).astype(int)
    else:
        predict_all = np.argmax(probs_all, axis=1)
    result = {'acc': metrics.accuracy_score(labels_all, predict_all)}
    precision = metrics.precision_score(labels_all, predict_all, average='macro', zero_division=0)
    recall = metrics.recall_score(labels_all, predict_all, average='macro', zero_division=0)
    f1 = metrics.f1_score(labels_all, predict_all, average='macro', zero_division=0)
    result.update({'precision': precision, 'recall': recall, 'f1': f1})
    if config.dataset == 'intent':
        for k in (3, 5):
            result[f'acc@{k}'] = metrics.top_k_accuracy_score(
                labels_all,
                probs_all,
                k=k,
                normalize=True,
                labels=range(len(config.class_list)),
            )
    return result


def train(config, model, train_iter, dev_iter, test_iter):
    start_time = time.time()
    model.train()
    param_optimizer = list(model.named_parameters())
    no_decay = ['bias', 'LayerNorm.bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in param_optimizer if not any(nd in n for nd in no_decay)], 'weight_decay': 0.01},
        {'params': [p for n, p in param_optimizer if any(nd in n for nd in no_decay)], 'weight_decay': 0.0}]

    optimizer = BertAdam(optimizer_grouped_parameters,
                         lr=config.learning_rate,
                         warmup=0.05,
                         t_total=len(train_iter) * config.num_epochs)
    class_weights = build_class_weights(config, train_iter)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    total_batch = 0
    dev_best_loss = float('inf')
    last_improve = 0  # 记录上次验证集loss下降的batch数
    flag = False  # 记录是否很久没有效果提升
    model.train()
    for epoch in range(config.num_epochs):
        logger.info('Epoch [{}/{}]'.format(epoch + 1, config.num_epochs))
        for i, (trains, labels) in enumerate(train_iter):
            outputs = model(trains)
            optimizer.zero_grad()
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
            optimizer.step()
            total_batch += 1
            if total_batch % config.eval_interval == 0 or i == len(train_iter) - 1:
                # 每多少轮输出在训练集和验证集上的效果
                true = labels.data.cpu()
                predic = torch.max(outputs.data, 1)[1].cpu()
                train_acc = metrics.accuracy_score(true, predic)
                dev_acc, dev_loss = evaluate(config, model, dev_iter, class_weights=class_weights)
                if dev_loss < dev_best_loss:
                    dev_best_loss = dev_loss
                    Path(config.save_path).parent.mkdir(parents=True, exist_ok=True)
                    torch.save(model.state_dict(), config.save_path)
                    improve = '*'
                    last_improve = total_batch
                else:
                    improve = ''
                time_dif = get_time_dif(start_time)
                msg = 'Iter: {0:>6},  Train Loss: {1:>5.2},  Train Acc: {2:>6.2%},  Val Loss: {3:>5.2},  Val Acc: {4:>6.2%},  Time: {5} {6}'
                logger.info(msg.format(total_batch, loss.item(), train_acc, dev_loss, dev_acc, time_dif, improve))
                model.train()
            if total_batch - last_improve > config.require_improvement:
                # 早停止
                logger.info("No optimization for a long time, auto-stopping...")
                flag = True
                break
        if flag:
            break

    return test(config, model, test_iter, dev_iter=dev_iter, class_weights=class_weights)


def test(config, model, test_iter, dev_iter=None, class_weights=None):
    # test
    logger.info("="* 50)
    model.load_state_dict(torch.load(config.save_path, map_location=config.device))
    model.eval()
    start_time = time.time()
    threshold = None
    if config.dataset == 'reject' and dev_iter is not None:
        dev_labels, dev_probs, _ = _collect_predictions(config, model, dev_iter, class_weights)
        threshold = find_best_threshold(dev_labels, dev_probs[:, 1])
        logger.info(f"Calibrated reject threshold: {threshold:.4f}")
    result = evaluate(
        config,
        model,
        test_iter,
        test=True,
        class_weights=class_weights,
        threshold=threshold,
    )
    if threshold is not None:
        result['threshold'] = threshold

    logger.info(f"Precision: {result['precision']}")
    logger.info(f"Recall: {result['recall']}")
    logger.info(f"F1: {result['f1']}")
    logger.info(f"Accuracy: {result['acc']}")
    if config.dataset == "intent":
        logger.info(f"Accuracy@3: {result['acc@3']}")
        logger.info(f"Accuracy@5: {result['acc@5']}")
    metrics_path = getattr(config, 'metrics_path', '')
    if metrics_path:
        report = {
            'dataset': config.dataset,
            'model': config.model_name,
            'device': str(config.device),
            'class_weighting': getattr(config, 'class_weighting', 'none'),
            'metrics': {key: float(value) for key, value in result.items()},
        }
        Path(metrics_path).parent.mkdir(parents=True, exist_ok=True)
        Path(metrics_path).write_text(json.dumps(report, indent=2), encoding='utf-8')
    time_dif = get_time_dif(start_time)
    logger.info(f"Time usage: {time_dif}")
    return result


def evaluate(config, model, data_iter, test=False, class_weights=None, threshold=None):
    labels_all, probs_all, loss = _collect_predictions(config, model, data_iter, class_weights)
    result = _classification_metrics(config, labels_all, probs_all, threshold=threshold)
    if test:
        return result
    return result['acc'], loss
