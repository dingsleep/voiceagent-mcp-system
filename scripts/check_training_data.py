"""Audit labels, duplicate samples, and split overlap without loading weights."""

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import argparse


ROOT = Path(__file__).resolve().parents[1]


def normalize_text(text):
    """Use the same lightweight normalization for duplicate and overlap checks."""
    return ''.join(text.split()).casefold()


def parse_rows(lines, class_count):
    rows = []
    invalid = 0
    for line in lines:
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 2:
            invalid += 1
            continue
        text = '\t'.join(parts[:-1]).strip()
        try:
            label = int(parts[-1].strip())
        except ValueError:
            invalid += 1
            continue
        if not text or not 0 <= label < class_count:
            invalid += 1
            continue
        rows.append((normalize_text(text), label))
    return rows, invalid


def summarize_rows(lines, class_count):
    counts = Counter()
    rows, invalid = parse_rows(lines, class_count)
    seen_pairs = set()
    labels_by_text = defaultdict(set)
    duplicate_rows = 0
    for text, label in rows:
        counts[label] += 1
        if (text, label) in seen_pairs:
            duplicate_rows += 1
        seen_pairs.add((text, label))
        labels_by_text[text].add(label)
    values = sorted(counts.values())
    return {
        'samples': sum(values),
        'used_classes': len(counts),
        'missing_classes': sorted(set(range(class_count)) - set(counts)),
        'invalid_rows': invalid,
        'min_class_size': values[0] if values else 0,
        'max_class_size': values[-1] if values else 0,
        'imbalance_ratio': round(values[-1] / values[0], 2) if values else 0,
        'duplicate_rows': duplicate_rows,
        'conflicting_texts': sum(len(labels) > 1 for labels in labels_by_text.values()),
    }


def audit_dataset(data_root, name):
    dataset = data_root / name
    class_count = len((dataset / 'class.txt').read_text(encoding='utf-8').splitlines())
    report = {}
    labels_by_split = {}
    for split in ('train', 'dev', 'test'):
        lines = (dataset / f'{split}.txt').read_text(encoding='utf-8').splitlines()
        report[split] = summarize_rows(lines, class_count)
        labels_by_text = defaultdict(set)
        for text, label in parse_rows(lines, class_count)[0]:
            labels_by_text[text].add(label)
        labels_by_split[split] = labels_by_text

    overlap = {}
    for left, right in combinations(labels_by_split, 2):
        shared = set(labels_by_split[left]) & set(labels_by_split[right])
        overlap[f'{left}/{right}'] = {
            'shared_texts': len(shared),
            'conflicting_labels': sum(
                labels_by_split[left][text] != labels_by_split[right][text]
                for text in shared
            ),
        }
    report['cross_split_overlap'] = overlap
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Audit training labels and class imbalance')
    parser.add_argument('--dataset', choices=('intent', 'reject'))
    parser.add_argument('--data-root', type=Path, default=ROOT / 'train' / 'data')
    parser.add_argument('--strict', action='store_true', help='fail when malformed or out-of-range rows exist')
    parser.add_argument('--fail-on-overlap', action='store_true', help='also fail when splits share text or labels conflict')
    args = parser.parse_args(argv)
    names = (args.dataset,) if args.dataset else ('intent', 'reject')
    failed = False
    for name in names:
        report = audit_dataset(args.data_root, name)
        for split in ('train', 'dev', 'test'):
            stats = report[split]
            print(
                f'{name}/{split}: samples={stats["samples"]}, '
                f'classes={stats["used_classes"]}, '
                f'missing={len(stats["missing_classes"])}, invalid={stats["invalid_rows"]}, '
                f'duplicates={stats["duplicate_rows"]}, conflicts={stats["conflicting_texts"]}, '
                f'imbalance={stats["imbalance_ratio"]}x'
            )
            failed |= stats['invalid_rows'] > 0
        for pair, stats in report['cross_split_overlap'].items():
            print(
                f'{name}/{pair}: shared_texts={stats["shared_texts"]}, '
                f'conflicting_labels={stats["conflicting_labels"]}'
            )
            if args.fail_on_overlap:
                failed |= bool(stats['shared_texts'] or stats['conflicting_labels'])
    return 1 if args.strict and failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
