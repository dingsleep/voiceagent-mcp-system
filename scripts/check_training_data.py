"""Audit class coverage and imbalance without loading model weights."""

from collections import Counter
from pathlib import Path
import argparse


ROOT = Path(__file__).resolve().parents[1]


def summarize_rows(lines, class_count):
    counts = Counter()
    invalid = 0
    for line in lines:
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 2:
            invalid += 1
            continue
        try:
            label = int(parts[-1].strip())
        except ValueError:
            invalid += 1
            continue
        if not 0 <= label < class_count:
            invalid += 1
            continue
        counts[label] += 1
    values = sorted(counts.values())
    return {
        'samples': sum(values),
        'used_classes': len(counts),
        'missing_classes': sorted(set(range(class_count)) - set(counts)),
        'invalid_rows': invalid,
        'min_class_size': values[0] if values else 0,
        'max_class_size': values[-1] if values else 0,
        'imbalance_ratio': round(values[-1] / values[0], 2) if values else 0,
    }


def audit_dataset(data_root, name):
    dataset = data_root / name
    class_count = len((dataset / 'class.txt').read_text(encoding='utf-8').splitlines())
    return {
        split: summarize_rows((dataset / f'{split}.txt').read_text(encoding='utf-8').splitlines(), class_count)
        for split in ('train', 'dev', 'test')
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit training labels and class imbalance')
    parser.add_argument('--dataset', choices=('intent', 'reject'))
    parser.add_argument('--strict', action='store_true', help='fail when malformed or out-of-range rows exist')
    args = parser.parse_args(argv)
    names = (args.dataset,) if args.dataset else ('intent', 'reject')
    failed = False
    for name in names:
        report = audit_dataset(ROOT / 'train' / 'data', name)
        for split, stats in report.items():
            print(
                f'{name}/{split}: samples={stats["samples"]}, '
                f'classes={stats["used_classes"]}, '
                f'missing={len(stats["missing_classes"])}, '
                f'invalid={stats["invalid_rows"]}, '
                f'imbalance={stats["imbalance_ratio"]}x'
            )
            failed |= stats['invalid_rows'] > 0
    return 1 if args.strict and failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
