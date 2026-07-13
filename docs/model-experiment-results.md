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

## Local Artifacts

The following files are intentionally ignored by Git:

```text
train/pretrained/**/pytorch_model.bin
train/saved/reject/bert_tiny.ckpt
train/saved/intent/bert.ckpt
```

Training creates machine-readable reports next to the checkpoints:

```text
train/saved/reject/bert_tiny.metrics.json
train/saved/intent/bert.metrics.json
```

Run `python scripts/check_release.py --strict` before publishing. It verifies
that local artifacts are excluded while source code, documentation, and checks
remain release-ready.
