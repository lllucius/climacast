# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

import logging
import os

from dotenv import load_dotenv
from typing import List

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


load_dotenv()


class Config:
    """
    Configuration class for managing environment variables and application settings.
    Provides a centralized location for all configuration values.

    Environment Variables:
        event_id: Event identifier for notifications
        app_id: Alexa skill application ID (default: amzn1.ask.skill.test)
        dataupdate_id: Data update identifier (default: amzn1.ask.data.update)
        here_api_key: HERE.com API key for geocoding
        DYNAMODB_PERSISTENCE_TABLE_NAME: DynamoDB table name (default: ask-{app_id})
        DYNAMODB_PERSISTENCE_REGION: AWS region (default: us-east-1)

    Example:
        Access configuration values:
            app_id = Config.APP_ID
            table_name = Config.DYNAMODB_TABLE_NAME
    """

    # Application identifiers
    EVENT_ID: str = os.environ.get("event_id", "")
    APP_ID: str = os.environ.get("app_id", "amzn1.ask.skill.test")
    DATA_UPDATE_ID: str = os.environ.get("dataupdate_id", "amzn1.ask.data.update")

    # API keys
    HERE_API_KEY: str = os.environ.get("here_api_key", "")

    # DynamoDB settings
    DYNAMODB_TABLE_NAME: str = os.environ.get(
        "DYNAMODB_PERSISTENCE_TABLE_NAME", f"ask-{os.environ.get('app_id', 'test')}"
    )
    DYNAMODB_REGION: str = os.environ.get("DYNAMODB_PERSISTENCE_REGION", "us-east-1")

    # Cache settings
    DEFAULT_CACHE_TTL_DAYS: int = 35

    # HTTP retry settings
    HTTP_RETRY_TOTAL: int = 3
    HTTP_RETRY_STATUS_CODES: List[int] = [429, 500, 502, 503, 504]
    HTTP_TIMEOUT: int = 30

    @classmethod
    def validate(cls):
        """
        Validate required configuration values.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Check for required values in production (not in test mode)
        is_test_mode = os.environ.get("SKILLTEST", "").lower() == "true"

        if not is_test_mode:
            if not cls.APP_ID or cls.APP_ID == "amzn1.ask.skill.test":
                logger.warning("APP_ID not set or using test value")

            if not cls.HERE_API_KEY:
                logger.warning("HERE_API_KEY not set - geocoding will not work")

            if not cls.DYNAMODB_TABLE_NAME:
                raise ValueError("DYNAMODB_TABLE_NAME must be set")

            if not cls.DYNAMODB_REGION:
                raise ValueError("DYNAMODB_REGION must be set")

        logger.info("Configuration validated successfully")


