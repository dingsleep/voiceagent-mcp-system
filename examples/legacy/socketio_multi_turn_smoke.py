# -*- coding: utf-8 -*-

import json
import os
import queue
import random
from pathlib import Path

import socketio
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
URL = os.environ["ENTRY_URL"]

sio = socketio.Client()
data_q = queue.Queue(2000)


@sio.on("connect")
def on_connect():
    print("connected to server")


@sio.on("disconnect")
def on_disconnect():
    print("disconnected from server")


@sio.on("message")
def on_message(data):
    print("Received message:", data)


@sio.on("error")
def on_error(error):
    print("Error:", error)


@sio.on("request_nlu")
def on_response(data):
    response = json.loads(data)
    data_q.put(response)
    print("Response:", response)


def rand_str(size=6):
    return "".join(random.sample("1234567890zyxwvutsrqponmlkjihgfedcba", size))


if __name__ == "__main__":
    input_path = ROOT / "test" / "data" / "multi_test.txt"
    output_path = ROOT / "test" / "result" / "multi_test_output.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open(encoding="utf-8") as fd, output_path.open("w", encoding="utf-8") as fw:
        for line in fd:
            sio.connect(URL)
            payload = {"sender_id": rand_str(9)}
            sessions = [text.strip() for text in line.split("\t") if text.strip()]
            for query in sessions:
                payload["trace_id"] = rand_str(9)
                payload["query"] = query
                payload["enable_dm"] = False
                sio.emit("request_nlu", json.dumps(payload, ensure_ascii=False))

                result = {"query": query, "res": []}
                response = data_q.get()
                result["res"].append(response)
                while response.get("intent") == "闲聊百科" and response.get("status") != 2:
                    response = data_q.get()
                    result["res"].append(response)

                fw.write(json.dumps(result, ensure_ascii=False) + "\n")
                fw.flush()
            sio.disconnect()

    print("done")
