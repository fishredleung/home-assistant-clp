import asyncio
import logging

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def verify_otp(session, email, otp, timeout=30):
    """Verify OTP and return token data or raise exception."""
    url = "https://api.clp.com.hk/ts2/ms/profile/accountManagement/passwordlesslogin/otpverify"
    json_payload = {
        "type": "email",
        "email": email,
        "otp": otp,
    }
    try:
        async with async_timeout.timeout(timeout):
            async with session.post(url, json=json_payload) as response:
                response.raise_for_status()
                data = await response.json()
                if not data or 'data' not in data:
                    raise ValueError('Invalid response data')
                _LOGGER.debug(f"OTP verification response: {data}")
                resp = data["data"]
                return {
                    "access_token": resp.get("accessToken") or resp.get("access_token"),
                    "refresh_token": resp.get("refreshToken") or resp.get("refresh_token"),
                    "access_token_expiry_time": resp.get("accessTokenExpiredAt")
                    or resp.get("access_token_expiry_time")
                    or resp.get("expires_in"),
                }
    except Exception as ex:
        _LOGGER.error(f"OTP verification failed: {ex}")
        raise

async def async_setup(hass: HomeAssistant, config: dict):
    session = async_get_clientsession(hass)
    hass.data[CONF_DOMAIN] = {
        "session": session
    }
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    if CONF_DOMAIN not in hass.data:
        session = async_get_clientsession(hass)
        hass.data[CONF_DOMAIN] = {
            "session": session,
            "access_token": entry.data.get("access_token"),
            "refresh_token": entry.data.get("refresh_token"),
            "access_token_expiry_time": entry.data.get("access_token_expiry_time"),
            "token_lock": asyncio.Lock(),
        }
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok and CONF_DOMAIN in hass.data:
        hass.data.pop(CONF_DOMAIN)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry):
    """Reload config entry when options or data change."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
