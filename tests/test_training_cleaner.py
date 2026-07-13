import tempfile
import unittest
from pathlib import Path

from scripts.prepare_training_data import clean_dataset


class TrainingCleanerTest(unittest.TestCase):
    def test_keeps_holdout_splits_and_removes_duplicates_and_conflicts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / 'data' / 'intent'
            source.mkdir(parents=True)
            (source / 'class.txt').write_text('a\nb\n', encoding='utf-8')
            (source / 'train.txt').write_text('train only\t0\nduplicate\t0\nduplicate\t0\nshared\t0\nconflict\t0\n', encoding='utf-8')
            (source / 'dev.txt').write_text('shared\t0\nconflict\t1\n', encoding='utf-8')
            (source / 'test.txt').write_text('test only\t1\n', encoding='utf-8')

            output_root = Path(temp_dir) / 'clean'
            report = clean_dataset(source.parent, output_root, 'intent', write=True)

            self.assertEqual(report['splits']['train']['written_rows'], 2)
            self.assertEqual(report['splits']['dev']['written_rows'], 1)
            self.assertEqual(report['splits']['test']['written_rows'], 1)
            self.assertEqual(
                (output_root / 'intent' / 'train.txt').read_text(encoding='utf-8'),
                'train only\t0\nduplicate\t0\n',
            )
            self.assertEqual((output_root / 'intent' / 'dev.txt').read_text(encoding='utf-8'), 'shared\t0\n')
