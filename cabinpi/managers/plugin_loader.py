"""
Dynamic plugin loader for CabinPython v2 daemon.

This module provides functionality to dynamically load sensor and output
plugins from configuration, instantiate them, and verify they implement
the required protocols.
"""

import importlib
import logging
from typing import Dict, Any, Type, Optional, Union

from cabinpi.core.protocols import SensorPlugin, OutputPlugin

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""
    pass


class PluginLoader:
    """
    Dynamically loads sensor and output plugins from configuration.

    The loader imports Python modules specified in config.yaml and
    instantiates plugin classes. It verifies that loaded plugins
    implement the required protocols (SensorPlugin or OutputPlugin).

    Example configuration:
        plugins:
          sensors:
            sht31:
              enabled: true
              module: cabinpi.plugins.sensors.sht31
              config:
                i2c_address: 0x44

    Example usage:
        >>> loader = PluginLoader()
        >>> plugin = loader.load_sensor_plugin("sht31", sensor_config)
        >>> assert isinstance(plugin, SensorPlugin)
    """

    def __init__(self) -> None:
        """Initialize the plugin loader."""
        self._loaded_modules: Dict[str, Any] = {}

    def load_sensor_plugin(
        self,
        plugin_id: str,
        plugin_config: Dict[str, Any]
    ) -> SensorPlugin:
        """
        Load and instantiate a sensor plugin.

        Args:
            plugin_id: Unique identifier for the plugin (e.g., "sht31")
            plugin_config: Configuration dict from config.yaml containing:
                - module: Python module path (e.g., "cabinpi.plugins.sensors.sht31")
                - config: Plugin-specific configuration (optional)
                - Other metadata (enabled, type, interval, etc.)

        Returns:
            Instantiated sensor plugin implementing SensorPlugin protocol

        Raises:
            PluginLoadError: If module can't be loaded or doesn't implement protocol
        """
        module_path = plugin_config.get("module")
        if not module_path:
            raise PluginLoadError(
                f"Sensor plugin '{plugin_id}' missing 'module' in configuration"
            )

        try:
            # Import the module
            module = self._import_module(module_path)

            # Find the plugin class (assumes module has a class matching convention)
            plugin_class = self._find_plugin_class(module, "Sensor")

            # Instantiate the plugin
            plugin = plugin_class(plugin_id)

            # Verify it implements SensorPlugin protocol
            if not isinstance(plugin, SensorPlugin):
                raise PluginLoadError(
                    f"Sensor plugin '{plugin_id}' from module '{module_path}' "
                    f"does not implement SensorPlugin protocol"
                )

            logger.info(f"Loaded sensor plugin: {plugin_id} from {module_path}")
            return plugin

        except ImportError as e:
            raise PluginLoadError(
                f"Failed to import sensor module '{module_path}': {e}"
            ) from e
        except Exception as e:
            raise PluginLoadError(
                f"Failed to load sensor plugin '{plugin_id}': {e}"
            ) from e

    def load_output_plugin(
        self,
        plugin_id: str,
        plugin_config: Dict[str, Any]
    ) -> OutputPlugin:
        """
        Load and instantiate an output plugin.

        Args:
            plugin_id: Unique identifier for the plugin (e.g., "database")
            plugin_config: Configuration dict from config.yaml containing:
                - module: Python module path (e.g., "cabinpi.plugins.outputs.mariadb_storage")
                - type: Output type (measurement_storage, event_log, notification)
                - config: Plugin-specific configuration (optional)

        Returns:
            Instantiated output plugin implementing OutputPlugin protocol

        Raises:
            PluginLoadError: If module can't be loaded or doesn't implement protocol
        """
        module_path = plugin_config.get("module")
        if not module_path:
            raise PluginLoadError(
                f"Output plugin '{plugin_id}' missing 'module' in configuration"
            )

        output_type = plugin_config.get("type")
        if not output_type:
            raise PluginLoadError(
                f"Output plugin '{plugin_id}' missing 'type' in configuration"
            )

        try:
            # Import the module
            module = self._import_module(module_path)

            # Find the plugin class
            plugin_class = self._find_plugin_class(module, "Output")

            # Instantiate the plugin
            plugin = plugin_class(plugin_id, output_type)

            # Verify it implements OutputPlugin protocol
            if not isinstance(plugin, OutputPlugin):
                raise PluginLoadError(
                    f"Output plugin '{plugin_id}' from module '{module_path}' "
                    f"does not implement OutputPlugin protocol"
                )

            logger.info(f"Loaded output plugin: {plugin_id} ({output_type}) from {module_path}")
            return plugin

        except ImportError as e:
            raise PluginLoadError(
                f"Failed to import output module '{module_path}': {e}"
            ) from e
        except Exception as e:
            raise PluginLoadError(
                f"Failed to load output plugin '{plugin_id}': {e}"
            ) from e

    def _import_module(self, module_path: str) -> Any:
        """
        Import a module by its path, with caching.

        Args:
            module_path: Python module path (e.g., "cabinpi.plugins.sensors.sht31")

        Returns:
            Imported module

        Raises:
            ImportError: If module cannot be imported
        """
        if module_path in self._loaded_modules:
            return self._loaded_modules[module_path]

        module = importlib.import_module(module_path)
        self._loaded_modules[module_path] = module
        return module

    def _find_plugin_class(self, module: Any, suffix: str) -> Type:
        """
        Find the plugin class in a module.

        Looks for classes ending with the specified suffix (e.g., "Sensor", "Output").
        If only one class is found in the module, uses that.

        Args:
            module: Imported Python module
            suffix: Expected class name suffix

        Returns:
            Plugin class type

        Raises:
            PluginLoadError: If no suitable class is found
        """
        # Get all classes from the module
        classes = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and obj.__module__ == module.__name__:
                classes.append((name, obj))

        if not classes:
            raise PluginLoadError(
                f"No classes found in module '{module.__name__}'"
            )

        # Look for class ending with suffix
        for name, cls in classes:
            if name.endswith(suffix):
                return cls

        # If only one class, use it
        if len(classes) == 1:
            return classes[0][1]

        # Multiple classes but none match suffix
        raise PluginLoadError(
            f"Multiple classes in module '{module.__name__}', "
            f"none ending with '{suffix}': {[name for name, _ in classes]}"
        )

    def unload_all(self) -> None:
        """
        Clear the module cache.

        Useful for testing or configuration reload scenarios.
        """
        self._loaded_modules.clear()
        logger.debug("Cleared plugin module cache")
