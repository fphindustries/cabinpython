#!/opt/cabinpython/env/bin/python3
"""
Sync sensor measurements from local MariaDB to Cloudflare-protected API.

This script reads unsynced measurements from the database and sends them
to the remote API endpoint, marking them as synced upon successful transmission.
"""

import sys
import logging
import argparse
import configparser
from sync_common import (
    get_unsynced_measurements,
    mark_as_synced,
    convert_measurement_to_api_format,
    send_to_api
)


def sync_all_records(config: configparser.ConfigParser, batch_size: int, client_id: str,
                     client_secret: str, api_url: str, test_mode: bool = False) -> tuple:
    """
    Sync all unsynced records to the remote API in batches.

    Args:
        config: Configuration object with database credentials
        batch_size: Number of records to process per batch
        client_id: Cloudflare Access Client ID
        client_secret: Cloudflare Access Client Secret
        api_url: API endpoint URL
        test_mode: If True, only process one batch

    Returns:
        Tuple of (total_synced, total_failed, batch_count)
    """
    total_synced = 0
    total_failed = 0
    batch_number = 0

    # Loop until no unsynced records remain (or just one batch in test mode)
    while True:
        batch_number += 1

        # Fetch unsynced measurements
        logging.info("Batch %d: Fetching up to %d unsynced measurements%s",
                     batch_number, batch_size, " (test mode)" if test_mode else "")
        records = get_unsynced_measurements(config, batch_size)

        if not records:
            logging.info("No more unsynced measurements found")
            break

        logging.info("Batch %d: Found %d unsynced measurements", batch_number, len(records))

        # Collect record dates (primary keys) and convert to API format
        record_dates = []
        api_measurements = []

        for record in records:
            record_date = record.get('Date')
            if not record_date:
                logging.warning("Skipping record without Date: %s", record)
                continue

            # Convert to API format
            api_payload = convert_measurement_to_api_format(record)
            api_measurements.append(api_payload)
            record_dates.append(record_date)

        if not api_measurements:
            logging.warning("No valid records to sync in this batch")
            break

        # Send all measurements in one batch
        logging.info("Batch %d: Sending %d measurements to API", batch_number, len(api_measurements))
        if send_to_api(api_measurements, api_url, client_id, client_secret):
            # Mark all records as synced
            success_count = 0
            fail_count = 0

            for record_date in record_dates:
                if mark_as_synced(config, record_date):
                    success_count += 1
                else:
                    fail_count += 1
                    logging.error("Failed to mark record with Date %s as synced", record_date)

            total_synced += success_count
            total_failed += fail_count

            logging.info(
                "Batch %d complete: %d successful, %d failed out of %d total",
                batch_number,
                success_count,
                fail_count,
                len(record_dates)
            )
        else:
            logging.error("Batch %d: Failed to send measurements to API", batch_number)
            total_failed += len(record_dates)

        # In test mode, only process one batch
        if test_mode:
            logging.info("Test mode: stopping after one batch")
            break

    return (total_synced, total_failed, batch_number)


def main(argv=None):
    """Main sync function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )

    parser = argparse.ArgumentParser(
        description='Sync sensor measurements to Cloudflare-protected API'
    )
    parser.add_argument(
        '--config',
        default='config.ini',
        help='Path to configuration file (default: config.ini)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of records to process per run (default: 10)'
    )
    parser.add_argument(
        '--api-url',
        default='https://cabinpi.com/api/sensors/ingest',
        help='API endpoint URL'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: only send 1 record and exit'
    )

    args = parser.parse_args(argv)

    # Load configuration
    config = configparser.ConfigParser()
    config.read(args.config)

    # Get Cloudflare credentials from config file
    try:
        client_id = config.get('CloudflareAccess', 'client_id')
        client_secret = config.get('CloudflareAccess', 'client_secret')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logging.error(
            "CloudflareAccess section with client_id and client_secret must be defined in config file"
        )
        sys.exit(1)

    # Determine batch size based on test mode
    batch_size = 1 if args.test else args.batch_size

    # Sync all records
    total_synced, total_failed, batch_count = sync_all_records(
        config, batch_size, client_id, client_secret, args.api_url, args.test
    )

    # Final summary
    logging.info(
        "Sync complete: %d batches processed, %d total synced, %d total failed%s",
        batch_count,
        total_synced,
        total_failed,
        " (test mode)" if args.test else ""
    )

    # Exit with error code if any failures
    if total_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
