"""
File-based logger output plugin.

This plugin writes sensor readings to JSON files for testing and debugging
without requiring a database. Useful for development and validation.

Output formats:
- JSON lines (one JSON object per line)
- Pretty JSON (formatted for readability)
- CSV (comma-separated values)
"""

import logging
import json
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import SensorReading

logger = logging.getLogger(__name__)


class FileLoggerOutput:
    """
    File-based logger output implementation.

    Implements the OutputPlugin protocol for writing sensor readings
    to files in various formats.

    Configuration example:
        file_logger:
          enabled: true
          type: measurement_storage
          module: cabinpi.plugins.outputs.file_logger
          config:
            file_path: "/tmp/sensor_readings.jsonl"
            format: "jsonl"  # jsonl, json, or csv
            pretty: false
            append: true
            max_size_mb: 100
    """

    def __init__(self, output_id: str, output_type: str) -> None:
        """
        Initialize the file logger output.

        Args:
            output_id: Unique output identifier
            output_type: Output type (should be "measurement_storage")
        """
        self._output_id = output_id
        self._output_type = output_type
        self._file_path: Optional[Path] = None
        self._format: str = "jsonl"
        self._pretty: bool = False
        self._append: bool = True
        self._max_size_mb: int = 100
        self._reading_count: int = 0

    @property
    def output_id(self) -> str:
        """Return the output ID."""
        return self._output_id

    @property
    def output_type(self) -> str:
        """Return the output type."""
        return self._output_type

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the file logger.

        Args:
            config: Configuration dict with:
                - file_path: Path to output file (default: /tmp/sensor_readings.jsonl)
                - format: Output format - "jsonl", "json", or "csv" (default: jsonl)
                - pretty: Pretty-print JSON (default: false)
                - append: Append to existing file (default: true)
                - max_size_mb: Max file size in MB before rotation (default: 100)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            file_path_str = config.get("file_path", "/tmp/sensor_readings.jsonl")
            self._file_path = Path(file_path_str)
            self._format = config.get("format", "jsonl").lower()
            self._pretty = config.get("pretty", False)
            self._append = config.get("append", True)
            self._max_size_mb = config.get("max_size_mb", 100)

            # Validate format
            if self._format not in ["jsonl", "json", "csv"]:
                logger.error(f"Invalid format: {self._format}. Must be jsonl, json, or csv")
                return False

            # Create parent directory
            self._file_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if file exists and handle append mode
            if self._file_path.exists() and not self._append:
                # Backup existing file
                backup_path = self._file_path.with_suffix(
                    f".{datetime.now().strftime('%Y%m%d_%H%M%S')}{self._file_path.suffix}"
                )
                self._file_path.rename(backup_path)
                logger.info(f"Backed up existing file to {backup_path}")

            # Initialize file based on format
            if self._format == "csv" and (not self._file_path.exists() or not self._append):
                # Create CSV with header
                self._write_csv_header()

            logger.info(
                f"File logger initialized: {self._file_path} "
                f"(format={self._format}, append={self._append})"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize file logger: {e}")
            return False

    def _write_csv_header(self) -> None:
        """Write CSV header row."""
        # Common columns for all sensors
        headers = [
            "timestamp",
            "sensor_id",
            "temp_c",
            "temp_f",
            "humidity",
            "current_a",
            "current_ma",
            "bus_voltage_v",
            "power_w",
            "power_mw",
            "device_id",
            "label",
            "error"
        ]

        with open(self._file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()

    def _rotate_if_needed(self) -> None:
        """Rotate file if it exceeds max size."""
        if not self._file_path.exists():
            return

        size_mb = self._file_path.stat().st_size / (1024 * 1024)
        if size_mb >= self._max_size_mb:
            # Rotate file
            rotated_path = self._file_path.with_suffix(
                f".{datetime.now().strftime('%Y%m%d_%H%M%S')}{self._file_path.suffix}"
            )
            self._file_path.rename(rotated_path)
            logger.info(f"Rotated log file to {rotated_path} ({size_mb:.1f} MB)")

            # Recreate header for CSV
            if self._format == "csv":
                self._write_csv_header()

    def _format_reading_jsonl(self, reading: SensorReading) -> str:
        """
        Format reading as JSON line.

        Args:
            reading: Sensor reading to format

        Returns:
            JSON string (single line)
        """
        data = {
            "timestamp": reading.timestamp.isoformat(),
            "sensor_id": reading.sensor_id,
            "measurements": reading.measurements,
            "error": reading.error
        }

        if self._pretty:
            return json.dumps(data, indent=2)
        else:
            return json.dumps(data)

    def _format_reading_csv(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Format reading as CSV row.

        Args:
            reading: Sensor reading to format

        Returns:
            Dictionary for CSV writer
        """
        row = {
            "timestamp": reading.timestamp.isoformat(),
            "sensor_id": reading.sensor_id,
            "error": reading.error or ""
        }

        # Add all measurements as columns
        row.update(reading.measurements)

        return row

    async def write(self, data: Any) -> bool:
        """
        Write sensor readings to file.

        Args:
            data: Either a single SensorReading or a list of SensorReading objects

        Returns:
            True if write succeeded
        """
        # Handle both single reading and list of readings
        if isinstance(data, list):
            readings = data
        else:
            readings = [data]

        return await self._write_readings(readings)

    async def _write_readings(self, readings: List[SensorReading]) -> bool:
        """
        Internal method to write sensor readings to file.

        Args:
            readings: List of sensor readings to write

        Returns:
            True if write succeeded
        """
        try:
            if not self._file_path:
                logger.error("File logger not initialized")
                return False

            # Check if rotation needed
            self._rotate_if_needed()

            # Filter valid readings (include errors for debugging)
            data_to_write = [r for r in readings if r.is_valid or r.error]

            if not data_to_write:
                logger.debug("No valid readings to write")
                return True

            # Write based on format
            if self._format == "jsonl":
                self._write_jsonl(data_to_write)
            elif self._format == "json":
                self._write_json(data_to_write)
            elif self._format == "csv":
                self._write_csv(data_to_write)

            self._reading_count += len(data_to_write)
            logger.debug(
                f"Wrote {len(data_to_write)} readings to {self._file_path} "
                f"(total: {self._reading_count})"
            )

            return True

        except Exception as e:
            logger.exception(f"Error writing to file: {e}")
            return False

    def _write_jsonl(self, readings: List[SensorReading]) -> None:
        """Write readings as JSON lines."""
        with open(self._file_path, 'a') as f:
            for reading in readings:
                line = self._format_reading_jsonl(reading)
                f.write(line + "\n")
                if self._pretty:
                    f.write("\n")  # Extra blank line for readability

    def _write_json(self, readings: List[SensorReading]) -> None:
        """Write readings as JSON array."""
        # Load existing data if appending
        existing_data = []
        if self._append and self._file_path.exists():
            try:
                with open(self._file_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        existing_data = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Could not parse existing JSON file, starting fresh")

        # Convert readings to dicts
        new_data = []
        for reading in readings:
            data = {
                "timestamp": reading.timestamp.isoformat(),
                "sensor_id": reading.sensor_id,
                "measurements": reading.measurements,
                "error": reading.error
            }
            new_data.append(data)

        # Combine and write
        all_data = existing_data + new_data

        with open(self._file_path, 'w') as f:
            if self._pretty:
                json.dump(all_data, f, indent=2)
            else:
                json.dump(all_data, f)

    def _write_csv(self, readings: List[SensorReading]) -> None:
        """Write readings as CSV rows."""
        # Get all possible field names from readings
        all_fields = set(["timestamp", "sensor_id", "error"])
        for reading in readings:
            all_fields.update(reading.measurements.keys())

        # Open in append mode
        mode = 'a' if self._append and self._file_path.exists() else 'w'

        with open(self._file_path, mode, newline='') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=sorted(all_fields),
                extrasaction='ignore'
            )

            # Write header if new file
            if mode == 'w':
                writer.writeheader()

            # Write rows
            for reading in readings:
                row = self._format_reading_csv(reading)
                writer.writerow(row)

    async def shutdown(self) -> None:
        """Close file logger."""
        try:
            logger.info(
                f"File logger shutdown complete. "
                f"Wrote {self._reading_count} total readings to {self._file_path}"
            )
        except Exception as e:
            logger.warning(f"Error during file logger shutdown: {e}")

    async def health_check(self) -> bool:
        """
        Check if file logger is healthy.

        Returns:
            True if file path is writable
        """
        try:
            if not self._file_path:
                return False

            # Check parent directory exists and is writable
            parent = self._file_path.parent
            return parent.exists() and parent.is_dir()

        except Exception as e:
            logger.debug(f"File logger health check failed: {e}")
            return False
