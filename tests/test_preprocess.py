import unittest
from app.nlp.preprocess import preprocess_text

class TestPreprocess(unittest.TestCase):

    def test_remove_stop_words(self):
        text = "This is a sample email text with some stop words."
        expected_output = "sample email text stop words."
        self.assertEqual(preprocess_text(text), expected_output)

    def test_stemming(self):
        text = "running runner ran"
        expected_output = "run run run"
        self.assertEqual(preprocess_text(text), expected_output)

    def test_lemmatization(self):
        text = "better best"
        expected_output = "good good"
        self.assertEqual(preprocess_text(text), expected_output)

if __name__ == '__main__':
    unittest.main()