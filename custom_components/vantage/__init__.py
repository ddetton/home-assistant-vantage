"""The Vantage InFusion Controller integration."""

from aiovantage import Vantage
from aiovantage.errors import (
    ClientConnectionError,
    LoginFailedError,
    LoginRequiredError,
)

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import async_setup_devices
from .entity import async_cleanup_entities

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.COVER,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vantage integration from a config entry."""

    # Create a Vantage client
    vantage = Vantage(
        entry.data[CONF_HOST],
        entry.data.get(CONF_USERNAME),
        entry.data.get(CONF_PASSWORD),
        use_ssl=entry.data.get(CONF_SSL, True),
    )

    # Store the client in the hass data store
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = vantage

    try:
        # Initialize and fetch all objects
        await vantage.initialize()

        # Add Vantage devices (controllers, modules, stations) to the device registry
        async_setup_devices(hass, entry)

        # Set up each platform (lights, covers, etc.)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Clean up any orphaned entities
        async_cleanup_entities(hass, entry)

    except (LoginRequiredError, LoginFailedError) as err:
        # Handle expired or invalid credentials. This will prompt the user to
        # reconfigure the integration.
        raise ConfigEntryAuthFailed from err

    except ClientConnectionError as err:
        # Handle offline or unavailable devices and services. Home Assistant will
        # automatically put the config entry in a failure state and start a reauth flow.
        raise ConfigEntryNotReady from err

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    vantage: Vantage = hass.data[DOMAIN].pop(entry.entry_id, None)
    if vantage:
        vantage.close()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
