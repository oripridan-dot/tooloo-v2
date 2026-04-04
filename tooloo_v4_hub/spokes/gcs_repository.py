# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: gcs_repository.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/spokes/gcs_repository.py
# WHEN: 2026-04-03T16:08:23.389956+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import os
from google.cloud import storage
from .repositories import ChatRepository

class GCSChatRepository(ChatRepository):
    """ChatRepository that syncs the SQLite DB to a GCS bucket.

    After each message store, the local ``chat.db`` file is uploaded to the bucket.
    On fetch, the latest DB is downloaded if not present locally.
    """

    def __init__(self, bucket_name: str, db_path: str = None):
        super().__init__(db_path)
        if not bucket_name:
            raise ValueError("GCS_BUCKET environment variable must be set for GCSChatRepository")
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    async def store_message(self, message):
        # Store locally first
        await super().store_message(message)
        # Upload the updated DB to GCS
        self.bucket.blob('chat.db').upload_from_filename(self.db_path)

    async def fetch_recent(self, limit: int = 50):
        # Ensure we have the latest DB from GCS before reading
        if not os.path.exists(self.db_path):
            self.bucket.blob('chat.db').download_to_filename(self.db_path)
        return await super().fetch_recent(limit)
