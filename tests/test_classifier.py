import unittest
from app.nlp.classifier import classify_email

class TestEmailClassifier(unittest.TestCase):

    def test_productive_email(self):
        email_content = "Could you please provide an update on my support ticket?"
        result = classify_email(email_content)
        self.assertEqual(result, "Produtivo")

    def test_unproductive_email(self):
        email_content = "Happy holidays! Wishing you all the best."
        result = classify_email(email_content)
        self.assertEqual(result, "Improdutivo")

    def test_edge_case_empty_email(self):
        email_content = ""
        result = classify_email(email_content)
        self.assertEqual(result, "Improdutivo")

    def test_edge_case_greeting_email(self):
        email_content = "Hello! Just checking in."
        result = classify_email(email_content)
        self.assertEqual(result, "Improdutivo")

if __name__ == '__main__':
    unittest.main()