"""Read pre-generated ESC/POS logo bytes. No runtime conversion."""

import logging
import os

_logger = logging.getLogger(__name__)

LOGO_RAW = "/images/pizzeria_logo_raw.escpos"
_cached = None


def get_logo_escpos_bytes():
    """Return cached ESC/POS logo bytes read from disk once."""
    global _cached
    if _cached is not None:
        return _cached
    if not os.path.exists(LOGO_RAW):
        _logger.error("Logo file not found: %s", LOGO_RAW)
        return None
    try:
        with open(LOGO_RAW, "rb") as f:
            _cached = f.read()
        _logger.info("Logo loaded: %d bytes", len(_cached))
        return _cached
    except Exception as e:
        _logger.error("Logo read failed: %s", e)
        return None
