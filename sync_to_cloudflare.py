#!/opt/cabinpython/env/bin/python3
"""
Sync sensor measurements from local MariaDB directly into Cloudflare D1.

This script reads unsynced measurements from the database and inserts them
directly into the Cloudflare D1 `measurements` table via the D1 HTTP API,
marking them as synced upon successful transmission.
"""

import sys
import logging
import argparse
import configparser
from sync_common import (
    get_unsynced_measurements,
    mark_as_synced,
    convert_measurement_to_d1_row,
    insert_measurements_to_d1
)


def sync_all_records(config: configparser.ConfigParser, batch_size: int, account_id: str,
                     database_id: str, api_token: str, test_mode: bool = False) -> tuple:
    """
    Sync all unsynced records directly into Cloudflare D1 in batches.

    Args:
        config: Configuration object with database credentials
        batch_size: Number of records to process per batch
        account_id: Cloudflare account ID
        database_id: Cloudflare D1 database UUID
        api_token: Cloudflare API token scoped with D1 edit permission
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

        # Collect record dates (primary keys) and convert to D1 row format
        record_dates = []
        d1_rows = []

        for record in records:
            record_date = record.get('Date')
            if not record_date:
                logging.warning("Skipping record without Date: %s", record)
                continue

            d1_rows.append(convert_measurement_to_d1_row(record))
            record_dates.append(record_date)

        if not d1_rows:
            logging.warning("No valid records to sync in this batch")
            break

        # Insert all measurements in one batch
        logging.info("Batch %d: Inserting %d measurements into D1", batch_number, len(d1_rows))
        if insert_measurements_to_d1(d1_rows, account_id, database_id, api_token):
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
            logging.error("Batch %d: Failed to insert measurements into D1", batch_number)
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
        description='Sync sensor measurements directly into Cloudflare D1'
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
        '--test',
        action='store_true',
        help='Test mode: only send 1 record and exit'
    )

    args = parser.parse_args(argv)

    # Load configuration
    config = configparser.ConfigParser()
    if not config.read(args.config):
        logging.error("Could not read configuration file: %s", args.config)
        sys.exit(1)

    # Get Cloudflare D1 credentials from config file
    try:
        account_id = config.get('CloudflareD1', 'account_id')
        database_id = config.get('CloudflareD1', 'database_id')
        api_token = config.get('CloudflareD1', 'api_token')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logging.error(
            "CloudflareD1 section with account_id, database_id and api_token "
            "must be defined in config file"
        )
        sys.exit(1)

    # Determine batch size based on test mode
    batch_size = 1 if args.test else args.batch_size

    # Sync all records
    total_synced, total_failed, batch_count = sync_all_records(
        config, batch_size, account_id, database_id, api_token, args.test
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
