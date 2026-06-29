from fastapi import APIRouter, HTTPException
import logging

from app.services.network_service import scan_network

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["network"])

@router.get("/network/scan")
async def scan_wifi_network():
    """
    Scan the local network for connected devices.
    Uses native ARP cache + ping sweep — no nmap needed.
    """
    try:
        devices = scan_network()
        return {"status": "ok", "devices": devices, "total": len(devices)}
    except Exception as e:
        logger.error(f"Error scanning network: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan network: {e}")
