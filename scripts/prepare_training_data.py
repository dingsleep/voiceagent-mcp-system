"""Create deduplicated, split-isolated training data without touching source files."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPLITS = ('train', 'dev', 'test')


def normalize_text(text):
    return ''.join(text.split()).casefold()


def load_rows(path, class_count):
    rows = []
    invalid_rows = 0
    for line in path.read_text(encoding='utf-8').splitlines():
        parts = line.split('\t')
        if len(parts) < 2:
            invalid_rows += 1
            continue
        text = '\t'.join(parts[:-1]).strip()
        try:
            label = int(parts[-1].strip())
        except ValueError:
            invalid_rows += 1
            continue
        if not text or not 0 <= label < class_count:
            invalid_rows += 1
            continue
        rows.append((normalize_text(text), label, line))
    return rows, invalid_rows


def clean_dataset(data_root, output_root, dataset, write=False, overwrite=False):
    source = Path(data_root) / dataset
    target = Path(output_root) / dataset
    class_file = source / 'class.txt'
    class_count = len(class_file.read_text(encoding='utf-8').splitlines())
    rows_by_split = {}
    labels_by_text = defaultdict(set)
    report = {'dataset': dataset, 'splits': {}}

    for split in SPLITS:
        rows, invalid_rows = load_rows(source / f'{split}.txt', class_count)
        rows_by_split[split] = rows
        for text, label, _ in rows:
            labels_by_text[text].add(label)
        report['splits'][split] = {'source_rows': len(rows), 'invalid_rows': invalid_rows}

    conflicting_texts = {text for text, labels in labels_by_text.items() if len(labels) > 1}
    claimed_texts = set()
    cleaned = {}
    for split in reversed(SPLITS):
        seen_pairs = set()
        kept = []
        removed = Counter()
        for text, label, line in rows_by_split[split]:
            if text in conflicting_texts:
                removed['conflicting_label'] += 1
            elif (text, label) in seen_pairs:
                removed['duplicate'] += 1
            elif text in claimed_texts:
                removed['split_overlap'] += 1
            else:
                seen_pairs.add((text, label))
                claimed_texts.add(text)
                kept.append(line)
        cleaned[split] = kept
        report['splits'][split].update({'written_rows': len(kept), 'removed': dict(removed)})
    report['conflicting_texts'] = len(conflicting_texts)

    if write:
        if target.exists() and not overwrite:
            raise FileExistsError(f'{target} already exists; pass --overwrite to replace this generated copy')
        target.mkdir(parents=True, exist_ok=True)
        (target / 'class.txt').write_text(class_file.read_text(encoding='utf-8'), encoding='utf-8')
        for split in SPLITS:
            (target / f'{split}.txt').write_text('\n'.join(cleaned[split]) + '\n', encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description='Create a deduplicated, split-isolated dataset copy')
    parser.add_argument('--dataset', choices=('intent', 'reject'), required=True)
    parser.add_argument('--data-root', type=Path, default=ROOT / 'train' / 'data')
    parser.add_argument('--output-root', type=Path, default=ROOT / 'train' / 'data_clean')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(argv)
    report = clean_dataset(
        args.data_root,
        args.output_root,
        args.dataset,
        write=not args.dry_run,
        overwrite=args.overwrite,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
