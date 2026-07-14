# Model Experiment Results

The original BERT training pipeline was executed locally before release. Large
weights and task checkpoints stay out of Git; this page preserves the commands
and measured results so reviewers can assess the model work without downloading
hundreds of megabytes.

## Environment

- Windows, NVIDIA GeForce RTX 4070 Ti SUPER
- Conda environment: `tx_agent`
- PyTorch: `2.5.1+cu121`
- GPU training enabled: `torch.cuda.is_available() == True`

## Reject Classifier

```bash
conda run -n tx_agent python -m train.run \
  --model bert_tiny --data reject --class-weighting none --seed 1
```

| Metric | Result |
| --- | ---: |
| Test accuracy | 89.26% |
| Macro precision | 89.26% |
| Macro recall | 89.42% |
| Macro F1 | 89.25% |
| Calibrated reject threshold | 0.5695 |

The threshold is selected from the validation split and is saved in the local
metrics report. The reject service uses it when a request omits `thres`.

## Intent Classifier

```bash
conda run -n tx_agent python -m train.run \
  --model bert --data intent --class-weighting none --seed 1
```

| Metric | Result |
| --- | ---: |
| Test accuracy | 85.99% |
| Macro precision | 89.26% |
| Macro recall | 85.63% |
| Macro F1 | 85.16% |
| Top-3 accuracy | 96.41% |
| Top-5 accuracy | 97.54% |

The top-k results are relevant because the downstream function-calling layer
can use ranked intent recall rather than only the first prediction.

## Clean Split Experiment (clean-v1)

The original data audit found duplicate queries and query overlap across
training, validation, and test splits. `clean-v1` removes duplicate
text/label pairs, removes text with conflicting labels, and assigns shared
text to `test`, then `dev`, before `train`. The original files remain intact.

| Dataset | Train | Dev | Test | Cross-split overlap |
| --- | ---: | ---: | ---: | ---: |
| Intent | 265,019 | 15,600 | 7,303 | 0 |
| Reject | 323,570 | 10,049 | 1,146 | 0 |

```bash
conda run -n tx_agent python scripts/prepare_training_data.py --dataset intent
conda run -n tx_agent python scripts/prepare_training_data.py --dataset reject
conda run -n tx_agent python -m train.run --model bert --data intent \
  --data-root train/data_clean --run-tag clean-v1
conda run -n tx_agent python -m train.run --model bert_tiny --data reject \
  --data-root train/data_clean --run-tag clean-v1
```

| Model | Accuracy | Macro F1 | Additional result |
| --- | ---: | ---: | --- |
| Intent `bert.clean-v1` | 86.17% | 82.76% | Top-3 96.03%, Top-5 97.23% |
| Intent `bert.clean-balanced-v1` | 87.79% | 85.18% | Top-3 97.04%, Top-5 97.92% |
| Reject `bert_tiny.clean-v1` | 89.09% | 88.69% | Calibrated threshold 0.6162 |

These scores are not directly comparable with the original results because
the test sets changed. The clean experiment is the trustworthy baseline for
future comparisons. On the same clean split, balanced cross-entropy improves
intent macro-F1 by 2.42 percentage points, so `clean-balanced-v1` is the
selected intent checkpoint. Its diagnostics show that the main remaining
errors are `set` versus `increase/decrease` seat controls, which is a focused
hard-negative data collection target.

The intent service prefers local `clean-balanced-v1`, then `clean-v1`, then
the original checkpoint. The reject service prefers `clean-v1`, then its
original checkpoint. Set `VOICE_AGENT_MODEL_TAG` to choose another local tag;
missing tagged weights fall back safely.

## Local Artifacts

The following files are intentionally ignored by Git:

```text
train/pretrained/**/pytorch_model.bin
train/saved/reject/bert_tiny.ckpt
train/saved/intent/bert.ckpt
train/saved/reject/bert_tiny.clean-v1.ckpt
train/saved/intent/bert.clean-v1.ckpt
train/saved/intent/bert.clean-balanced-v1.ckpt
```

Training creates machine-readable reports next to the checkpoints:

```text
train/saved/reject/bert_tiny.metrics.json
train/saved/intent/bert.metrics.json
train/saved/reject/bert_tiny.clean-v1.metrics.json
train/saved/intent/bert.clean-v1.metrics.json
train/saved/intent/bert.clean-balanced-v1.metrics.json
```

Run `python scripts/check_release.py --strict` before publishing. It verifies
that local artifacts are excluded while source code, documentation, and checks
remain release-ready.
