# Training And Evaluation

The repository keeps the original BERT intent classifier and the lightweight
reject classifier. Training data, model code, service adapters, and offline
evaluation are separate so a model change can be verified without starting
the full LLM/MCP runtime.

## Train

Run commands from the repository root:

```bash
python -m train.run --model bert --data intent --seed 1
python -m train.run --model bert_tiny --data reject --seed 1
```

Useful overrides for a smoke run or a controlled experiment:

```bash
python -m train.run --model bert_tiny --data reject \
  --epochs 1 --batch-size 32 --learning-rate 5e-5 --seed 7
```

For long-tail intent experiments, enable balanced cross-entropy weights:

```bash
python -m train.run --model bert --data intent --class-weighting balanced
```

The default is `none` so the original training behavior remains the baseline.
Compare macro-F1 and top-k recall before choosing the weighted checkpoint.

For the reject model, the best probability threshold is selected on the
validation split and stored in the metrics report. The reject service uses
that calibrated threshold when a request does not provide `thres` explicitly.

After a successful training run, the test metrics are also written to
`train/saved/<dataset>/<model>.metrics.json` next to the ignored checkpoint.
This keeps experiment comparisons machine-readable without committing model
weights.

The training entrypoint now resolves `train/data`, `train/pretrained`, and
`train/saved` from the repository location, so the command is independent of
the current working directory. The seed controls NumPy, PyTorch, and CUDA
randomness. The best checkpoint is selected by validation macro-F1, with
validation loss used only to break ties, and is written under
`train/saved/<dataset>/`, which is intentionally ignored by Git.

## Metrics

`train/train_eval.py` reports accuracy, macro precision, macro recall, and
macro F1 on the test split. Intent classification also reports top-3 and top-5
accuracy because the downstream function-calling layer can use ranked intent
recall. Validation runs periodically and at the end of every epoch, so small
datasets still produce a checkpoint.

Audit label coverage before training:

```bash
python scripts/check_training_data.py
python scripts/check_training_data.py --dataset intent --strict
python scripts/check_training_data.py --dataset intent --fail-on-overlap
```

The audit normalizes whitespace before counting duplicate rows and reports
text shared by `train`, `dev`, and `test`. Use `--fail-on-overlap` when
preparing a clean experiment split; it remains opt-in because some legacy
datasets contain repeated templates.

Each training metrics JSON now contains class-level precision/recall/F1 and
the ten most frequent confusion pairs. This directly identifies the next
data-cleaning or hard-negative collection task.

Create a cleaned experiment copy before retraining a dataset with leakage:

```bash
python scripts/prepare_training_data.py --dataset intent --dry-run
python scripts/prepare_training_data.py --dataset intent
python -m train.run --model bert --data intent \
  --data-root train/data_clean --run-tag clean-v1
```

The cleaner keeps the original files unchanged, removes repeated text/label
pairs, removes text with conflicting labels, and gives `test` then `dev`
priority over `train` when the same text appears in multiple splits. Generated
copies and their experiment checkpoints are ignored by Git.

The existing HTTP benchmark scripts in `test/` measure service throughput
with Locust. The offline mock pipeline has a dependency-free functional check:

```bash
python eval/evaluate_demo.py
```

## Model artifacts

Large checkpoint files are not committed. Keep the code, configuration, class
lists, vocabularies, and data in Git; distribute trained weights through a
private artifact store, GitHub Releases, or Git LFS when the project needs
reproducible deployment.

The training stack still uses the original local BERT implementation and
dataset format. This is deliberate: it preserves compatibility with the
legacy intent/reject services while making the experiment entrypoint and
evaluation contract easier to inspect.
