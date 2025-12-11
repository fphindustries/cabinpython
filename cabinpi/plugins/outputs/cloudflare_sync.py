"""
Cloudflare API sync output plugin.

This plugin syncs measurements to a remote API protected by Cloudflare Access.
It batches multiple sensor readings and sends them to the API endpoint.

API:
- Endpoint: Configurable (e.g., https://cabinpi.com/api/sensors/ingest)
- Authentication: Cloudflare Access (client ID and secret)
- Format: JSON with camelCase field names
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import SensorReading

logger = logging.getLogger(__name__)


class CloudflareSyncOutput:
    """
    Cloudflare API sync output implementation.

    Implements the OutputPlugin protocol for syncing sensor readings
    to a remote API endpoint protected by Cloudflare Access.

    Configuration example:
        cloudflare_sync:
          enabled: true
          module: cabinpi.plugins.outputs.cloudflare_sync
          type: measurement_storage
          config:
            api_url: https://cabinpi.com/api/sensors/ingest
            client_id: "${CF_CLIENT_ID}"
            client_secret: "${CF_CLIENT_SECRET}"
            batch_size: 10
            timeout: 30
    """

    def __init__(self, output_id: str, output_type: str) -> None:
        """
        Initialize the Cloudflare sync output.

        Args:
            output_id: Unique output identifier
            output_type: Output type (should be "measurement_storage")
        """
        self._output_id = output_id
        self._output_type = output_type
        self._client: Optional[httpx.AsyncClient] = None
        self._api_url: str = ""
        self._client_id: str = ""
        self._client_secret: str = ""
        self._batch_size: int = 10
        self._timeout: int = 30
        self._batch: List[Dict[str, Any]] = []

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
        Initialize the HTTP client and API configuration.

        Args:
            config: Configuration dict with:
                - api_url: API endpoint URL
                - client_id: Cloudflare Access client ID
                - client_secret: Cloudflare Access client secret
                - batch_size: Number of measurements per batch (default: 10)
                - timeout: Request timeout in seconds (default: 30)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._api_url = config.get("api_url", "")
            self._client_id = config.get("client_id", "")
            self._client_secret = config.get("client_secret", "")
            self._batch_size = config.get("batch_size", 10)
            self._timeout = config.get("timeout", 30)

            if not self._api_url:
                logger.error("Cloudflare API URL not configured")
                return False

            if not self._client_id or not self._client_secret:
                logger.error("Cloudflare Access credentials not configured")
                return False

            # Create HTTP client
            self._client = httpx.AsyncClient(timeout=self._timeout)

            logger.info(f"Cloudflare sync initialized: {self._api_url}")
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize Cloudflare sync: {e}")
            return False

    async def write(self, data: Any) -> bool:
        """
        Write a sensor reading to the API (batched).

        Readings are batched and sent when batch_size is reached.

        Args:
            data: SensorReading object to write

        Returns:
            True if write succeeded (or batched for later)
        """
        if not isinstance(data, SensorReading):
            logger.error(f"Expected SensorReading, got {type(data)}")
            return False

        if not data.is_valid:
            logger.debug(f"Skipping invalid reading from {data.sensor_id}")
            return True

        try:
            # Convert reading to API format
            api_record = self._convert_to_api_format(data)

            # Add to batch
            self._batch.append(api_record)

            # Send batch if it's full
            if len(self._batch) >= self._batch_size:
                return await self._send_batch()

            # Successfully batched
            return True

        except Exception as e:
            logger.exception(f"Error batching measurement for Cloudflare sync: {e}")
            return False

    def _convert_to_api_format(self, reading: SensorReading) -> Dict[str, Any]:
        """
        Convert SensorReading to API's expected format.

        Converts snake_case to camelCase and flattens structure.

        Args:
            reading: SensorReading to convert

        Returns:
            Dictionary in API format
        """
        measurements = reading.measurements

        # Convert timestamp to ISO format
        date_value = reading.timestamp.isoformat()

        # Build API payload (camelCase, flat structure)
        payload = {
            "date": date_value,
            # Solar charge controller data
            "ampHours": measurements.get('AmpHours'),
            "batteryState": measurements.get('batteryState'),
            "chargeState": measurements.get('chargeState'),
            "classicState": measurements.get('classicState'),
            "dispavgVbatt": measurements.get('dispavgVbatt'),
            "dispavgVpv": measurements.get('dispavgVpv'),
            "ibattDisplay": measurements.get('IbattDisplay'),
            "kwhours": measurements.get('kWHours'),
            "niteMinutesNoPwr": measurements.get('NiteMinutesNoPwr'),
            "pvInputCurrent": measurements.get('PvInputCurrent'),
            "vocLastMeasured": measurements.get('VocLastMeasured'),
            "watts": measurements.get('watts'),
            "absorbTime": measurements.get('AbsorbTime'),
            "equalizeTime": measurements.get('EqualizeTime'),
            "floatTime": measurements.get('FloatTime'),
            "highestVinputLog": measurements.get('HighestVinputLog'),
            "battTemperature": measurements.get('BATTtemperature'),
            "lifeTimekWHours": measurements.get('LifeTimekWHours'),
            "lifetimeAmpHours": measurements.get('LifetimeAmpHours'),
            # Indoor sensor data
            "intC": measurements.get('int_c'),
            "intF": measurements.get('int_f'),
            "humidity": measurements.get('humidity'),
            # External weather data
            "avgStrikeDistance": measurements.get('avg_strike_distance'),
            "dailyAccumulation": measurements.get('daily_accumulation'),
            "extF": measurements.get('ext_temp'),
            "extHumidity": measurements.get('ext_humidity'),
            "illuminance": measurements.get('illuminance'),
            "inHg": measurements.get('pressure'),
            "rain": measurements.get('rain'),
            "solarRadiation": measurements.get('solar_radiation'),
            "strikeCount": measurements.get('strike_count'),
            "uv": measurements.get('uv'),
            "windAvg": measurements.get('wind_avg'),
            "windDirection": measurements.get('wind_direction'),
            "windGust": measurements.get('wind_gust'),
            "weatherBattery": measurements.get('weather_battery'),
            # Inverter data
            "inverterAacOut": measurements.get('InverterAACOut'),
            "inverterFault": measurements.get('InverterFault'),
            "inverterMode": measurements.get('InverterMode'),
            "inverterOn": measurements.get('InverterOn'),
            "inverterVacOut": measurements.get('InverterVACOut'),
            "invertervdc": measurements.get('Invertervdc'),
        }

        # Remove None values to keep payload clean
        return {k: v for k, v in payload.items() if v is not None}

    async def _send_batch(self) -> bool:
        """
        Send batched measurements to the API.

        Returns:
            True if send succeeded
        """
        if not self._batch:
            return True

        if not self._client:
            logger.error("HTTP client not initialized")
            return False

        try:
            # Build headers with Cloudflare Access credentials
            headers = {
                'CF-Access-Client-Id': self._client_id,
                'CF-Access-Client-Secret': self._client_secret,
                'Content-Type': 'application/json'
            }

            # Wrap measurements in records array
            payload = {
                'records': self._batch
            }

            # Send to API
            response = await self._client.post(
                self._api_url,
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            inserted = result.get('inserted', 0)
            total = result.get('total', 0)

            logger.info(
                f"Cloudflare sync: sent {len(self._batch)} measurements, "
                f"{inserted}/{total} inserted"
            )

            # Clear batch on success
            self._batch.clear()
            return True

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Cloudflare API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except httpx.TimeoutException:
            logger.error("Cloudflare API request timeout")
            return False
        except Exception as e:
            logger.exception(f"Error sending to Cloudflare API: {e}")
            return False

    async def shutdown(self) -> None:
        """Close HTTP client and flush any remaining batch."""
        try:
            # Send any remaining measurements
            if self._batch:
                logger.info(f"Flushing {len(self._batch)} remaining measurements")
                await self._send_batch()

            # Close HTTP client
            if self._client:
                await self._client.aclose()
                self._client = None
                logger.info("Cloudflare sync connection closed")

        except Exception as e:
            logger.warning(f"Error during Cloudflare sync shutdown: {e}")
