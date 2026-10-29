import unittest
from decimal import Decimal
from services.order_service.app import money, EMAIL_RE, ALLOWED_STATUSES

class OrderValidationTests(unittest.TestCase):
    def test_money_rounding(self):
        self.assertEqual(money("12.345"), Decimal("12.35"))
        self.assertEqual(money("12.344"), Decimal("12.34"))

    def test_email_validation(self):
        self.assertTrue(EMAIL_RE.match("coffee@example.com"))
        self.assertFalse(EMAIL_RE.match("not-an-email"))
        self.assertFalse(EMAIL_RE.match("coffee @example.com"))

    def test_allowed_statuses(self):
        self.assertIn("PENDING", ALLOWED_STATUSES)
        self.assertIn("COMPLETED", ALLOWED_STATUSES)
        self.assertNotIn("PAID", ALLOWED_STATUSES)

if __name__ == "__main__":
    unittest.main()
