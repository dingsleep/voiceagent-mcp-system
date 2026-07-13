"""Naming helpers for local experiment checkpoints and metrics."""

from pathlib import Path


def tagged_paths(checkpoint_path, metrics_path, run_tag):
    if not run_tag.replace('-', '').replace('_', '').replace('.', '').isalnum():
        raise ValueError('run tag may contain only letters, numbers, dots, dashes, and underscores')
    checkpoint = Path(checkpoint_path)
    metrics = Path(metrics_path)
    model_name = checkpoint.stem
    return (
        str(checkpoint.with_name(f'{model_name}.{run_tag}{checkpoint.suffix}')),
        str(metrics.with_name(f'{model_name}.{run_tag}.metrics.json')),
    )


def prefer_existing_tag(checkpoint_path, metrics_path, run_tag):
    if not run_tag:
        return checkpoint_path, metrics_path
    tagged_checkpoint, tagged_metrics = tagged_paths(checkpoint_path, metrics_path, run_tag)
    if Path(tagged_checkpoint).is_file():
        return tagged_checkpoint, tagged_metrics
    return checkpoint_path, metrics_path
