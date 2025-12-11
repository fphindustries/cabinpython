"""
WeatherFlow weather station sensor plugin.

This plugin reads weather data from the WeatherFlow API
using httpx for async HTTP requests.

API:
- Base URL: https://swd.weatherflow.com/swd/rest/observations
- Requires device ID and API token
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx

from cabinpi.core.protocols import SensorPlugin
from cabinpi.core.models import SensorReading, SensorType
from cabinpi.utils.conversions import (
    mps_to_mph,
    mb_to_inhg,
    celsius_to_fahrenheit,
    mm_to_inches,
    km_to_miles
)

logger = logging.getLogger(__name__)


class WeatherFlowSensor:
    """
    WeatherFlow weather station sensor implementation.

    Implements the SensorPlugin protocol for reading weather data
    from the WeatherFlow API.

    Configuration example:
        weather:
          enabled: true
          module: cabinpi.plugins.sensors.weatherflow
          type: api
          interval: 300
          config:
            device_id: "12345"
            api_token: "${WEATHER_TOKEN}"
            timeout: 10
    """

    API_BASE = "https://swd.weatherflow.com/swd/rest/observations"

    def __init__(self, sensor_id: str) -> None:
        """
        Initialize the weather sensor.

        Args:
            sensor_id: Unique sensor identifier
        """
        self._sensor_id = sensor_id
        self._client: Optional[httpx.AsyncClient] = None
        self._device_id: Optional[str] = None
        self._api_token: Optional[str] = None
        self._timeout: int = 10

    @property
    def sensor_id(self) -> str:
        """Return the sensor ID."""
        return self._sensor_id

    @property
    def sensor_type(self) -> SensorType:
        """Return sensor type (API)."""
        return SensorType.API

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the weather API client.

        Args:
            config: Configuration dict with:
                - device_id: WeatherFlow device ID
                - api_token: API authentication token
                - timeout: Request timeout in seconds (default: 10)

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._device_id = config.get("device_id")
            self._api_token = config.get("api_token")
            self._timeout = config.get("timeout", 10)

            if not self._device_id:
                logger.error("WeatherFlow device_id not configured")
                return False

            if not self._api_token:
                logger.error("WeatherFlow api_token not configured")
                return False

            # Create HTTP client
            self._client = httpx.AsyncClient(timeout=self._timeout)

            logger.info(f"WeatherFlow sensor initialized for device {self._device_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize WeatherFlow sensor: {e}")
            return False

    async def read(self) -> SensorReading:
        """
        Read weather data from WeatherFlow API.

        Returns:
            SensorReading with measurements including:
                - Wind speed/direction
                - Temperature and humidity
                - Pressure
                - Precipitation
                - Lightning data
                - Solar radiation and UV
        """
        try:
            if not self._client:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Weather API client not initialized"
                )

            # Build API URL
            url = f"{self.API_BASE}/device/{self._device_id}"
            params = {"token": self._api_token}

            # Make API request
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            if not data or 'obs' not in data or not data['obs']:
                return SensorReading(
                    sensor_id=self._sensor_id,
                    timestamp=datetime.now(),
                    measurements={},
                    error="Invalid weather API response"
                )

            # Extract observation data (most recent observation)
            obs = data['obs'][0]

            # Parse and convert units
            # obs array indices based on WeatherFlow API documentation
            measurements = {
                'wind_avg': round(mps_to_mph(obs[2]), 2),                    # Wind speed avg (mph)
                'wind_gust': round(mps_to_mph(obs[3]), 2),                   # Wind gust (mph)
                'wind_direction': obs[4],                                     # Wind direction (degrees)
                'pressure': round(mb_to_inhg(obs[6]), 2),                    # Pressure (inHg)
                'ext_temp': round(celsius_to_fahrenheit(obs[7]), 2),         # Temperature (F)
                'ext_humidity': obs[8],                                       # Humidity (%)
                'illuminance': obs[9],                                        # Light (lux)
                'uv': obs[10],                                                # UV index
                'solar_radiation': obs[11],                                   # Solar radiation (W/m²)
                'rain': round(mm_to_inches(obs[12]), 3),                     # Rain rate (in/hr)
                'avg_strike_distance': round(km_to_miles(obs[14]), 2),       # Lightning distance (miles)
                'strike_count': obs[15],                                      # Lightning count
                'weather_battery': obs[16],                                   # Battery voltage (V)
                'daily_accumulation': round(mm_to_inches(obs[18]), 3)        # Daily rain (inches)
            }

            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements=measurements
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"WeatherFlow API HTTP error: {e.response.status_code}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=f"HTTP {e.response.status_code}: {e.response.text}"
            )
        except httpx.TimeoutException:
            logger.error("WeatherFlow API request timeout")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error="API request timeout"
            )
        except Exception as e:
            logger.exception(f"Error reading WeatherFlow data: {e}")
            return SensorReading(
                sensor_id=self._sensor_id,
                timestamp=datetime.now(),
                measurements={},
                error=str(e)
            )

    async def shutdown(self) -> None:
        """Close HTTP client."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
                logger.info("WeatherFlow sensor shutdown complete")
        except Exception as e:
            logger.warning(f"Error shutting down WeatherFlow sensor: {e}")

    async def health_check(self) -> bool:
        """
        Check if WeatherFlow API is accessible.

        Returns:
            True if API is reachable
        """
        try:
            if not self._client:
                return False

            # Try to make a simple API request
            url = f"{self.API_BASE}/device/{self._device_id}"
            params = {"token": self._api_token}

            response = await self._client.get(url, params=params, timeout=5.0)
            return response.status_code == 200

        except Exception as e:
            logger.debug(f"WeatherFlow health check failed: {e}")
            return False
