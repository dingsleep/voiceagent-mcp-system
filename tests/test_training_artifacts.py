import tempfile
import unittest
from pathlib import Path

from train.artifacts import prefer_existing_tag, tagged_paths


class TrainingArtifactsTest(unittest.TestCase):
    def test_tagged_paths_keep_model_and_metrics_names_aligned(self):
        checkpoint, metrics = tagged_paths('train/saved/intent/bert.ckpt', 'train/saved/intent/bert.metrics.json', 'clean-v1')
        self.assertEqual(Path(checkpoint), Path('train/saved/intent/bert.clean-v1.ckpt'))
        self.assertEqual(Path(metrics), Path('train/saved/intent/bert.clean-v1.metrics.json'))

    def test_existing_tag_is_preferred_and_missing_tag_falls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint = root / 'bert.ckpt'
            metrics = root / 'bert.metrics.json'
            tagged_checkpoint, _ = tagged_paths(checkpoint, metrics, 'clean-v1')
            Path(tagged_checkpoint).touch()
            selected_checkpoint, _ = prefer_existing_tag(checkpoint, metrics, 'clean-v1')
            self.assertEqual(selected_checkpoint, tagged_checkpoint)
            fallback_checkpoint, _ = prefer_existing_tag(checkpoint, metrics, 'missing')
            self.assertEqual(fallback_checkpoint, checkpoint)
