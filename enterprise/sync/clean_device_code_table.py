"""
Cleanup script for device code table.

This script removes expired device codes from the database. Device codes are considered
expired if they are past their expires_at time.

The cleanup is limited to a maximum number of codes to avoid overwhelming the database.

Usage:
    python sync/clean_device_code_table.py

This script should be run periodically (e.g., via cron job) to maintain database hygiene.
"""

import asyncio

from storage.database import session_maker
from storage.device_code_store import DeviceCodeStore

LIMIT = 100  # Maximum number of device codes to delete


async def main():
    device_code_store = DeviceCodeStore(session_maker)
    deleted_count = device_code_store.cleanup_stale_device_codes(limit=LIMIT)
    print(f'Cleanup completed. Deleted {deleted_count} expired device codes.')


if __name__ == '__main__':
    asyncio.run(main())
