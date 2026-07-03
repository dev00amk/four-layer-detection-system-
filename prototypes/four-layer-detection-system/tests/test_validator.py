import unittest

from src.layer1_ingestion.validator import (
    TransactionValidationError,
    validate_transaction,
)


class ValidatorTests(unittest.TestCase):
    """Exercise valid and invalid Layer 1 boundary payloads."""
    def test_valid_payload_is_normalized(self) -> None:
        transaction = validate_transaction(
            {
                "transaction_id": " TXN-1 ",
                "user_id": " USER-1 ",
                "amount": 125,
                "currency": "usd",
                "timestamp": "2026-07-03T12:00:00+00:00",
            }
        )

        self.assertEqual(transaction["transaction_id"], "TXN-1")
        self.assertEqual(transaction["user_id"], "USER-1")
        self.assertEqual(transaction["amount"], 125.0)
        self.assertEqual(transaction["currency"], "USD")
        self.assertEqual(transaction["timestamp"], "2026-07-03T12:00:00Z")

    def test_missing_required_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            TransactionValidationError, "missing required fields: user_id"
        ):
            validate_transaction(
                {
                    "transaction_id": "TXN-1",
                    "amount": 125.0,
                    "currency": "USD",
                    "timestamp": "2026-07-03T12:00:00Z",
                }
            )

    def test_invalid_timestamp_is_rejected(self) -> None:
        with self.assertRaisesRegex(TransactionValidationError, "valid ISO-8601"):
            validate_transaction(
                {
                    "transaction_id": "TXN-1",
                    "user_id": "USER-1",
                    "amount": 125.0,
                    "currency": "USD",
                    "timestamp": "not-a-date",
                }
            )


if __name__ == "__main__":
    unittest.main()
