"""Unit tests for MongoDB connection setup."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pymongo.errors import ServerSelectionTimeoutError

from app.core.mongo import connect_mongodb


class MongoConnectionTests(unittest.TestCase):
    @patch("app.core.mongo.settings")
    def test_connection_is_skipped_when_mongodb_is_not_configured(
        self,
        mock_settings: Mock,
    ) -> None:
        mock_settings.mongodb_configured = False

        with patch("app.core.mongo.MongoClient") as mongo_client:
            self.assertEqual(connect_mongodb(), (None, None))

        mongo_client.assert_not_called()

    @patch("app.core.mongo.settings")
    @patch("app.core.mongo.MongoClient")
    def test_configured_connection_is_verified(
        self,
        mongo_client_factory: Mock,
        mock_settings: Mock,
    ) -> None:
        mock_settings.mongodb_configured = True
        mock_settings.MONGO_URI = "mongodb://localhost"
        mock_settings.MONGO_DB = "library"
        mock_settings.MONGO_SERVER_SELECTION_TIMEOUT_MS = 5000
        client = mongo_client_factory.return_value
        database = SimpleNamespace()
        client.__getitem__.return_value = database

        actual_client, actual_database = connect_mongodb()

        self.assertIs(actual_client, client)
        self.assertIs(actual_database, database)
        mongo_client_factory.assert_called_once_with(
            "mongodb://localhost",
            serverSelectionTimeoutMS=5000,
        )
        client.admin.command.assert_called_once_with("ping")
        client.close.assert_not_called()

    @patch("app.core.mongo.settings")
    @patch("app.core.mongo.MongoClient")
    def test_failed_connection_is_closed_and_error_is_propagated(
        self,
        mongo_client_factory: Mock,
        mock_settings: Mock,
    ) -> None:
        mock_settings.mongodb_configured = True
        mock_settings.MONGO_URI = "mongodb://localhost"
        mock_settings.MONGO_DB = "library"
        mock_settings.MONGO_SERVER_SELECTION_TIMEOUT_MS = 5000
        client = mongo_client_factory.return_value
        error = ServerSelectionTimeoutError("MongoDB unavailable")
        client.admin.command.side_effect = error

        with self.assertRaises(ServerSelectionTimeoutError) as raised:
            connect_mongodb()

        self.assertIs(raised.exception, error)
        client.close.assert_called_once_with()
