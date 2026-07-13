# -*- coding:utf-8 -*-

import os
from pathlib import Path
import re
import json
import random
import requests
import base64
import time
import torch
import uvicorn
import numpy as np
import torch.nn.functional as F
from importlib import import_module
from fastapi import FastAPI, Request
from utils import logger

try:
    from train.artifacts import prefer_existing_tag
    from train.data_helper import encode_text
except ImportError:
    from artifacts import prefer_existing_tag
    from data_helper import encode_text


## 创建FastAPI应用
app = FastAPI()


dataset = "reject" # 数据
model_name = "bert_tiny"  # 模型
try:
    x = import_module('train.models.' + model_name)
except ImportError:
    x = import_module('models.' + model_name)
config = x.Config(dataset)
config.save_path, config.metrics_path = prefer_existing_tag(
    config.save_path,
    config.metrics_path,
    os.getenv('VOICE_AGENT_MODEL_TAG', 'clean-v1'),
)
model = None
PAD, CLS = '[PAD]', '[CLS]'


def _load_threshold():
    try:
        report = json.loads(Path(config.metrics_path).read_text(encoding='utf-8'))
        return float(report.get('metrics', {}).get('threshold', 0.5))
    except (OSError, ValueError, TypeError):
        return 0.5


DEFAULT_THRESHOLD = _load_threshold()


def _get_model():
    global model
    if model is None:
        if not os.path.exists(config.save_path):
            raise FileNotFoundError(f'model checkpoint not found: {config.save_path}')
        model = x.Model(config).to(config.device)
        model.load_state_dict(torch.load(config.save_path, map_location=config.device))
        model.eval()
    return model


def predict(query, threshold):
    with torch.no_grad():
        token_ids, seq_len, mask = encode_text(config, query)
        x = torch.LongTensor([token_ids]).to(config.device)
        seq_len = torch.LongTensor([seq_len]).to(config.device)
        mask = torch.LongTensor([mask]).to(config.device)
        texts = (x, seq_len, mask)
        output = _get_model()(texts)
        prob = F.softmax(output,dim=-1).cpu().numpy()[0][1]
        predict = 1 if prob >= threshold else 0

        return predict, prob


@app.post("/reject-server/v1")
async def inference(request: Request):
    json_info = await request.json()
    query = json_info.get("query")
    trace_id = json_info.get("trace_id")
    thres = json_info.get("thres", DEFAULT_THRESHOLD)

    result = {}
    try:
        response, score = predict(query, float(thres))
    except:
        response, score = 1, 1.0

    result["data"] = response
    result["score"] = str(score)
    logger.info("Trace ID: {}, Request: {}, response: {}, confidence: {}".format(
        trace_id, query, result["data"], result["score"]))

    return result 


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8007, workers=1)
