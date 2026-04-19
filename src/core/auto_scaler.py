"""
Auto-scaling engine for Nemo Tracker.

Provisions new VPN nodes when load thresholds are exceeded.
Currently uses stub provisioning (logs actions without creating real servers).
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger
from sqlalchemy import select, func, desc

from src.models import async_session
from src.models.database import (
    ScalingPolicy, ScalingEvent, Server,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_server_loads() -> list[dict]:
    """Return load info for all active servers."""
    from src.core import server_manager

    servers = await server_manager.get_all_servers()
    loads = []
    for srv in servers:
        if not srv.is_active:
            continue
        stats = await server_manager.get_server_stats(srv.id) or {}
        loads.append({
            "id": srv.id,
            "name": srv.name,
            "current_users": srv.current_users or 0,
            "max_users": srv.max_users,
            "total_bandwidth": srv.total_bandwidth or 0,
            "status": srv.status,
            "stats": stats,
        })
    return loads


async def _count_active_servers() -> int:
    async with async_session() as session:
        return await session.scalar(
            select(func.count(Server.id)).where(Server.is_active == True)
        ) or 0


# ---------------------------------------------------------------------------
# Stub provisioning (logs actions, does not create real servers)
# ---------------------------------------------------------------------------

async def _provision_hetzner(token: str, server_type: str, region: str, image_id: Optional[str] = None) -> dict:
    """STUB: Provision a VPS via Hetzner Cloud API.

    Returns fake server info for logging/testing.
    """
    logger.info(
        f"[STUB] Provisioning Hetzner server: type={server_type}, region={region}, image={image_id}"
    )
    logger.info("[STUB] Would call: POST https://api.hetzner.cloud/v1/servers")
    ts = datetime.utcnow().strftime('%Y%m%d%H%M')
    logger.info(f"[STUB] Body: server_type={server_type}, location={region}, "
                f"image={image_id or 'ubuntu-22.04'}, name=vpn-node-auto-{ts}")

    fake_ip = f"10.0.{hash(datetime.utcnow().isoformat()) % 255}.{hash(server_type) % 255}"
    fake_server_id = hash(datetime.utcnow().isoformat()) % 100000

    logger.info(f"[STUB] Server would be created: id={fake_server_id}, ip={fake_ip}")
    return {
        "id": fake_server_id,
        "ip": fake_ip,
        "name": f"vpn-node-auto",
        "status": "running",
    }


async def _install_marzban(ip: str, ssh_key: Optional[str] = None) -> dict:
    """STUB: Install Docker + Marzban on a server via SSH."""
    logger.info(f"[STUB] Installing Marzban on {ip}")
    logger.info("[STUB] Would SSH and run:")
    logger.info("[STUB]   apt update && apt install -y docker.io docker-compose")
    logger.info("[STUB]   curl -L -o /opt/marzban/docker-compose.yml <template_url>")
    logger.info("[STUB]   cd /opt/marzban && docker compose up -d")
    return {"success": True, "url": f"http://{ip}:8000"}


async def _copy_config(source_server_id: int, target_ip: str) -> dict:
    """STUB: Copy inbound configuration from master server to new node."""
    logger.info(f"[STUB] Copying config from server {source_server_id} to {target_ip}")
    logger.info("[STUB] Would fetch inbounds from master Marzban API")
    logger.info("[STUB] Would POST inbounds to new node Marzban API")
    return {"success": True, "inbounds_copied": 0}


async def _register_server(name: str, ip: str, marzban_url: str, policy: ScalingPolicy) -> Optional[int]:
    """Register the new server in the database."""
    from src.core import server_manager

    srv = await server_manager.add_server(
        name=name,
        url=marzban_url,
        username="admin",
        password="auto-generated",
        ip_address=ip,
        country=policy.region,
        max_users=policy.scale_up_threshold_users,
    )
    return srv.id if srv else None


# ---------------------------------------------------------------------------
# Main check function
# ---------------------------------------------------------------------------

async def check_and_scale() -> list[dict]:
    """Check all enabled policies and scale up/down if needed.

    Returns list of actions taken.
    """
    actions = []

    async with async_session() as session:
        policies = (await session.execute(
            select(ScalingPolicy).where(ScalingPolicy.enabled == True)
        )).scalars().all()

        if not policies:
            return actions

        server_loads = await _get_server_loads()
        active_count = len(server_loads) or await _count_active_servers()

        for policy in policies:
            action_taken = await _check_policy(policy, server_loads, active_count, session)
            if action_taken:
                actions.append(action_taken)

    return actions


async def _check_policy(
    policy: ScalingPolicy,
    server_loads: list[dict],
    active_count: int,
    session,
) -> Optional[dict]:
    """Check a single policy and trigger scaling if needed."""

    now = datetime.utcnow()

    # Check cooldown
    if policy.last_scaled_at:
        cooldown_end = policy.last_scaled_at + timedelta(minutes=policy.cooldown_minutes)
        if now < cooldown_end:
            return None

    # Calculate current load metrics
    total_users = sum(s["current_users"] for s in server_loads)
    avg_cpu = 0  # We don't have real CPU data; use user load as proxy
    bandwidth_pct = 0

    if server_loads:
        for sl in server_loads:
            max_u = sl.get("max_users") or policy.scale_up_threshold_users
            if max_u > 0:
                avg_cpu = max(avg_cpu, (sl["current_users"] / max_u) * 100)

    should_scale_up = (
        active_count < policy.max_nodes and (
            avg_cpu >= policy.scale_up_threshold_cpu or
            total_users >= policy.scale_up_threshold_users * active_count
        )
    )

    should_scale_down = (
        active_count > policy.min_nodes and
        avg_cpu < policy.scale_up_threshold_cpu * 0.3 and
        total_users < policy.scale_up_threshold_users * active_count * 0.3
    )

    if should_scale_up:
        return await _do_scale_up(policy, server_loads, session)
    elif should_scale_down:
        return await _do_scale_down(policy, server_loads, session)

    return None


async def _do_scale_up(policy: ScalingPolicy, server_loads: list[dict], session) -> dict:
    """Execute scale-up (stub)."""
    now = datetime.utcnow()

    event = ScalingEvent(
        policy_id=policy.id,
        action="scale_up",
        status="provisioning",
        details=json.dumps({"reason": "threshold_exceeded"}),
    )
    session.add(event)
    await session.flush()
    event_id = event.id

    try:
        # Stub: provision server
        result = await _provision_hetzner(
            token=policy.provider_api_token or "",
            server_type=policy.server_type,
            region=policy.region or "fsn1",
            image_id=policy.image_id,
        )
        ip = result["ip"]

        # Stub: install marzban
        install_result = await _install_marzban(ip)

        # Stub: copy config from master
        master = next((s for s in server_loads if s.get("is_master")), server_loads[0] if server_loads else None)
        if master:
            await _copy_config(master["id"], ip)

        # Register in DB
        marzban_url = install_result.get("url", f"http://{ip}:8000")
        server_id = await _register_server(
            name=f"auto-node-{now.strftime('%Y%m%d%H%M')}",
            ip=ip,
            marzban_url=marzban_url,
            policy=policy,
        )

        event.server_id = server_id
        event.status = "ready"
        event.details = json.dumps({
            "reason": "threshold_exceeded",
            "ip": ip,
            "server_id": server_id,
            "provider_result": result,
        })
        event.completed_at = now
        policy.last_scaled_at = now
        await session.commit()

        logger.info(f"[Auto-scaler] Scale-up complete: event={event_id}, server={server_id}")
        return {"action": "scale_up", "event_id": event_id, "server_id": server_id, "ip": ip}

    except Exception as e:
        event.status = "failed"
        event.details = json.dumps({"reason": "threshold_exceeded", "error": str(e)})
        event.completed_at = datetime.utcnow()
        await session.commit()
        logger.error(f"[Auto-scaler] Scale-up failed: {e}")
        return {"action": "scale_up", "event_id": event_id, "error": str(e)}


async def _do_scale_down(policy: ScalingPolicy, server_loads: list[dict], session) -> dict:
    """Execute scale-down (stub)."""
    now = datetime.utcnow()

    # Find least loaded server (skip master)
    candidates = [s for s in server_loads if s["current_users"] == min(sl["current_users"] for sl in server_loads)]
    target = candidates[0] if candidates else None

    if not target:
        return {"action": "scale_down", "skipped": True, "reason": "no_candidates"}

    event = ScalingEvent(
        policy_id=policy.id,
        action="scale_down",
        server_id=target["id"],
        status="pending",
        details=json.dumps({"reason": "low_load", "target_server": target["name"]}),
    )
    session.add(event)
    await session.flush()

    try:
        logger.info(f"[STUB] Scale-down: would migrate users from {target['name']} and remove server")
        logger.info("[STUB] Would: 1) Move users to other nodes 2) Delete server via provider API 3) Remove from DB")

        event.status = "ready"
        event.completed_at = now
        policy.last_scaled_at = now
        await session.commit()

        return {"action": "scale_down", "event_id": event.id, "server_id": target["id"]}

    except Exception as e:
        event.status = "failed"
        event.completed_at = datetime.utcnow()
        await session.commit()
        return {"action": "scale_down", "event_id": event.id, "error": str(e)}


# ---------------------------------------------------------------------------
# Dry run (for testing UI)
# ---------------------------------------------------------------------------

async def dry_run() -> dict:
    """Simulate a scaling check without making changes."""
    server_loads = await _get_server_loads()
    active_count = len(server_loads)

    async with async_session() as session:
        policies = (await session.execute(
            select(ScalingPolicy).where(ScalingPolicy.enabled == True)
        )).scalars().all()

    decisions = []
    for policy in policies:
        total_users = sum(s["current_users"] for s in server_loads)
        avg_load = 0
        if server_loads:
            loads = []
            for sl in server_loads:
                max_u = sl.get("max_users") or policy.scale_up_threshold_users
                if max_u > 0:
                    loads.append((sl["current_users"] / max_u) * 100)
            avg_load = sum(loads) / len(loads) if loads else 0

        would_scale_up = (
            active_count < policy.max_nodes and (
                avg_load >= policy.scale_up_threshold_cpu or
                total_users >= policy.scale_up_threshold_users * active_count
            )
        )

        decisions.append({
            "policy_id": policy.id,
            "policy_name": policy.name,
            "active_servers": active_count,
            "total_users": total_users,
            "avg_load_pct": round(avg_load, 1),
            "would_scale_up": would_scale_up,
            "would_scale_down": (
                active_count > policy.min_nodes and
                avg_load < policy.scale_up_threshold_cpu * 0.3
            ),
        })

    return {
        "total_servers": active_count,
        "total_users": sum(s["current_users"] for s in server_loads),
        "decisions": decisions,
    }
