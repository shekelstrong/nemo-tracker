"""Subscription log parser — extracts IPs from Marzban access logs.

Monitors GET /sub/ requests to track real client IPs for all users,
including VIP tier (whitelist) where Xray only sees the proxy IP.
"""

import re
from typing import Optional
from loguru import logger


# Pattern: 95.26.26.69:0 - "GET /sub/dXNlcl81NTky... HTTP/1.1" 200 OK
# Also: 95.72.208.123:0 - "GET /sub/dXNlcl8yMDQ4... HTTP/1.1" 200 OK
SUB_PATTERN = re.compile(
    r'^([\d.]+):\d+\s*-\s*".*GET\s+/sub/(\S+)"'
)


def parse_sub_request(log_line: str) -> Optional[dict]:
    """Parse a Marzban access log line for subscription request.
    
    Returns dict with ip and sub_token, or None.
    """
    match = SUB_PATTERN.search(log_line)
    if not match:
        return None
    
    ip = match.group(1)
    sub_token = match.group(2)
    
    if ip.startswith(("127.", "10.", "172.", "192.168.", "0.")):
        return None
    
    return {
        "ip": ip,
        "sub_token": sub_token,
    }


def extract_username_from_sub_token(token: str, username_list: list[str]) -> Optional[str]:
    """Try to match a sub token to a username.
    
    Marzban sub tokens are base64-encoded and contain the username.
    We match by looking up known users' subscription URLs.
    """
    # This will be implemented by comparing with cached sub URLs from Marzban API
    return None
