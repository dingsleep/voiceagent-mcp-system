import unittest

from scripts.check_training_data import summarize_rows


class TrainingAuditTest(unittest.TestCase):
    def test_reports_missing_and_invalid_labels(self):
        result = summarize_rows(['a\t0', 'b\t0', 'c\t2', 'broken'], class_count=2)
        self.assertEqual(result['samples'], 2)
        self.assertEqual(result['used_classes'], 1)
        self.assertEqual(result['missing_classes'], [1])
        self.assertEqual(result['invalid_rows'], 2)


if __name__ == '__main__':
    unittest.main()
