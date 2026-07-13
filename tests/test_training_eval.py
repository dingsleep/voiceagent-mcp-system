import unittest
from types import SimpleNamespace

import numpy as np

from train.train_eval import _is_better_checkpoint, build_error_analysis, find_best_threshold


class TrainingEvalTest(unittest.TestCase):
    def test_reject_threshold_is_selected_from_validation_probabilities(self):
        labels = np.array([0, 0, 1, 1])
        probabilities = np.array([0.1, 0.4, 0.45, 0.6])
        self.assertEqual(find_best_threshold(labels, probabilities), 0.45)

    def test_checkpoint_selection_prefers_macro_f1_then_loss(self):
        self.assertTrue(_is_better_checkpoint(0.82, 0.5, 0.81, 0.1))
        self.assertTrue(_is_better_checkpoint(0.81, 0.4, 0.81, 0.5))
        self.assertFalse(_is_better_checkpoint(0.81, 0.6, 0.81, 0.5))

    def test_error_analysis_reports_top_confusion(self):
        config = SimpleNamespace(dataset='intent', num_classes=3, class_list=['a', 'b', 'c'])
        labels = np.array([0, 1, 2])
        probabilities = np.array([[0.1, 0.8, 0.1], [0.1, 0.8, 0.1], [0.1, 0.3, 0.6]])
        analysis = build_error_analysis(config, labels, probabilities)
        self.assertEqual(analysis['top_confusions'][0]['actual_label'], 'a')
        self.assertEqual(analysis['top_confusions'][0]['predicted_label'], 'b')
        self.assertEqual(len(analysis['per_class']), 3)


if __name__ == '__main__':
    unittest.main()
