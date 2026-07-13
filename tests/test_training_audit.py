import unittest

from scripts.check_training_data import summarize_rows


class TrainingAuditTest(unittest.TestCase):
    def test_reports_missing_and_invalid_labels(self):
        result = summarize_rows(['a\t0', 'b\t0', 'c\t2', 'broken'], class_count=2)
        self.assertEqual(result['samples'], 2)
        self.assertEqual(result['used_classes'], 1)
        self.assertEqual(result['missing_classes'], [1])
        self.assertEqual(result['invalid_rows'], 2)

    def test_reports_normalized_duplicates_and_label_conflicts(self):
        result = summarize_rows(['same text\t0', 'same   text\t0', 'same text\t1'], class_count=2)
        self.assertEqual(result['duplicate_rows'], 1)
        self.assertEqual(result['conflicting_texts'], 1)


if __name__ == '__main__':
    unittest.main()
