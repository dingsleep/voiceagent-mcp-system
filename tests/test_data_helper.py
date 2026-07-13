import unittest

import torch

from train.data_helper import DatasetIterater, encode_text


class FakeTokenizer:
    def tokenize(self, text):
        return list(text)

    def convert_tokens_to_ids(self, tokens):
        return list(range(1, len(tokens) + 1))


class Config:
    tokenizer = FakeTokenizer()
    pad_size = 4
    batch_size = 5
    device = torch.device('cpu')


class DataHelperTest(unittest.TestCase):
    def test_encode_text_truncates_and_pads(self):
        token_ids, seq_len, mask = encode_text(Config, 'abcdef')
        self.assertEqual(token_ids, [1, 2, 3, 4])
        self.assertEqual(seq_len, 4)
        self.assertEqual(mask, [1, 1, 1, 1])

    def test_iterator_handles_dataset_smaller_than_batch(self):
        rows = [([1, 0, 0, 0], 2, 1, [1, 0, 0, 0])]
        iterator = DatasetIterater(rows, batch_size=5, device=torch.device('cpu'))
        batches = list(iterator)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0][0][0].shape, (1, 4))
        self.assertEqual(batches[0][1].tolist(), [2])


if __name__ == '__main__':
    unittest.main()
