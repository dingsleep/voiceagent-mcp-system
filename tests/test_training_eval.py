import unittest

import numpy as np

from train.train_eval import find_best_threshold


class TrainingEvalTest(unittest.TestCase):
    def test_reject_threshold_is_selected_from_validation_probabilities(self):
        labels = np.array([0, 0, 1, 1])
        probabilities = np.array([0.1, 0.4, 0.45, 0.6])
        self.assertEqual(find_best_threshold(labels, probabilities), 0.45)


if __name__ == '__main__':
    unittest.main()
