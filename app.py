"""
Kavach-Edge — Main FastAPI Application
=======================================
Real-time infrastructure security monitoring with anomaly detection,
cryptographic audit ledger, chaos injection, and AI-powered SOP copilot.
All processing runs offline/locally with no external API dependencies.
"""
from __future__ import annotations
import asyncio
import time
import uuid
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)
# ---------------------------------------------------------------------------
# Local module imports (built in parallel)
# ---------------------------------------------------------------------------
from simulator import InfrastructureSimulator
from detector import AnomalyDetector
from ledger import CryptoLedger
from copilot import SOPCopilot
# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------
class ChaosRequest(BaseModel):
    """Payload for injecting a chaos / attack scenario into a node."""
    node_id: str
    attack_type: str
class ResolveRequest(BaseModel):
    """Payload for marking a node incident as resolved."""
    node_id: str
class CopilotQuery(BaseModel):
    """Payload for querying the SOP copilot."""
    query: str
# ---------------------------------------------------------------------------
# Global singletons — initialised during the lifespan startup phase
# ---------------------------------------------------------------------------
simulator: InfrastructureSimulator | None = None
detector: AnomalyDetector | None = None
ledger_store: CryptoLedger | None = None
copilot: SOPCopilot | None = None
# In-memory alert store — persists for the lifetime of the process
alerts: list[dict[str, Any]] = []
# Track new alerts between WebSocket pushes
_new_alert_buffer: list[dict[str, Any]] = []
# Startup timestamp for uptime calculation
_start_time: float = 0.0
# Background-task cancellation handle
_bg_task: asyncio.Task | None = None
# ---------------------------------------------------------------------------
# Background telemetry loop
# ---------------------------------------------------------------------------
async def _telemetry_loop() -> None:
    """Continuously update telemetry, run anomaly detection, and record alerts.
    Runs every ~1 second. Each iteration:
    1. Asks the simulator to refresh node telemetry.
    2. Runs the anomaly detector against every node.
    3. If an anomaly is flagged, classifies the threat, fetches remediation
       guidance, creates an alert record, and appends it to the crypto-ledger.
    """
    global alerts, _new_alert_buffer
    while True:
        try:
            if simulator and detector and ledger_store and copilot:
                # 1. Refresh simulated telemetry
                nodes = simulator.get_nodes()
                for node in nodes:
                    # 2. Run anomaly detection
                    anomaly_result: dict[str, Any] = detector.detect(node)
                    if anomaly_result.get("is_anomaly"):
                        # 3. Classify threat & build alert
                        threat_type = detector.get_threat_classification(
                            node, anomaly_result
                        )
                        remediation = copilot.get_remediation(
                            threat_type, node.get("type", "unknown")
                        )
                        alert: dict[str, Any] = {
                            "id": str(uuid.uuid4()),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "node_id": node.get("id", ""),
                            "node_name": node.get("name", "Unknown"),
                            "threat_type": threat_type,
                            "severity": anomaly_result.get("severity", "medium"),
                            "anomaly_score": anomaly_result.get("score", 0.0),
                            "remediation_summary": (
                                remediation.get("summary", "")
                                if isinstance(remediation, dict)
                                else str(remediation)
                            ),
                        }
                        alerts.append(alert)
                        _new_alert_buffer.append(alert)
                        # 4. Persist to crypto-ledger
                        ledger_store.add_entry(
                            event_type="anomaly_detected",
                            node_id=node.get("id", ""),
                            details={
                                "threat_type": threat_type,
                                "anomaly_score": anomaly_result.get("score", 0.0),
                            },
                            severity=anomaly_result.get("severity", "medium"),
                        )
        except Exception as exc:  # noqa: BLE001
            # Log but never crash the background loop
            print(f"[telemetry-loop] error: {exc}")
        await asyncio.sleep(1)
# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise singletons on startup and tear down the background task on shutdown."""
    global simulator, detector, ledger_store, copilot, _start_time, _bg_task
    # --- Startup -----------------------------------------------------------
    simulator = InfrastructureSimulator()
    detector = AnomalyDetector()
    ledger_store = CryptoLedger()
    copilot = SOPCopilot()
    _start_time = time.time()
    _bg_task = asyncio.create_task(_telemetry_loop())
    print("[kavach-edge] All modules initialised — background telemetry running.")
    yield
    # --- Shutdown ----------------------------------------------------------
    if _bg_task is not None:
        _bg_task.cancel()
        try:
            await _bg_task
        except asyncio.CancelledError:
            pass
    print("[kavach-edge] Shutdown complete.")
# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Kavach-Edge",
    description="Edge-native infrastructure security monitoring platform.",
    version="1.0.0",
    lifespan=lifespan,
)
# CORS — permissive for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Static file serving
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _build_stats() -> dict[str, Any]:
    """Compute summary statistics across all nodes."""
    nodes = simulator.get_nodes() if simulator else []
    healthy = sum(1 for n in nodes if n.get("status") == "healthy")
    warning = sum(1 for n in nodes if n.get("status") == "warning")
    critical = sum(1 for n in nodes if n.get("status") == "critical")
    integrity = False
    if ledger_store:
        try:
            integrity = ledger_store.verify_integrity()
        except Exception:  # noqa: BLE001
            integrity = False
    return {
        "total_nodes": len(nodes),
        "healthy_nodes": healthy,
        "warning_nodes": warning,
        "critical_nodes": critical,
        "total_alerts": len(alerts),
        "ledger_integrity_status": "valid" if integrity else "compromised",
        "uptime_seconds": round(time.time() - _start_time, 2),
    }
# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return FileResponse("static/index.html")
@app.get("/traffic")
async def traffic_dashboard():
    return FileResponse("static/traffic.html")
@app.get("/air-quality")
async def air_dashboard():
    return FileResponse("static/air.html")
@app.get("/ambulance")
async def ambulance_dashboard():
    return FileResponse("static/ambulance.html")
@app.get("/agriculture")
async def agri_dashboard():
    return FileResponse("static/agri.html")
# ---------------------------------------------------------------------------
# Routes — REST API
# ---------------------------------------------------------------------------
@app.get("/api/nodes", tags=["Nodes"])
async def get_nodes() -> list[dict[str, Any]]:
    """Return every node with current metrics, status, GPS coords, and anomaly results."""
    if not simulator or not detector:
        return []
    nodes = simulator.get_nodes()
    enriched: list[dict[str, Any]] = []
    for node in nodes:
        anomaly_result = detector.detect(node)
        enriched.append({
            **node,
            "anomaly": anomaly_result,
        })
    return enriched
@app.get("/api/telemetry", tags=["Telemetry"])
async def get_telemetry() -> dict[str, Any]:
    """Return the last 60 telemetry data-points per node."""
    if not simulator:
        return {"history": []}
    return {"history": simulator.get_telemetry_history()}
@app.post("/api/inject-chaos", tags=["Chaos Engineering"])
async def inject_chaos(body: ChaosRequest) -> dict[str, Any]:
    """Inject a chaos / attack scenario into the specified node."""
    if not simulator or not ledger_store:
        return {"success": False, "detail": "System not ready"}
    try:
        result = simulator.inject_chaos(body.node_id, body.attack_type)
        ledger_store.add_entry(
            event_type="chaos_injected",
            node_id=body.node_id,
            details={"attack_type": body.attack_type},
            severity="high",
        )
        return {
            "success": True,
            "node_id": body.node_id,
            "attack_type": body.attack_type,
            "result": result,
        }
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "detail": str(exc)}
@app.post("/api/resolve", tags=["Incident Response"])
async def resolve_node(body: ResolveRequest) -> dict[str, Any]:
    """Mark a node's incident as resolved and log the action."""
    if not simulator or not ledger_store:
        return {"success": False, "detail": "System not ready"}
    try:
        result = simulator.resolve_node(body.node_id)
        ledger_store.add_entry(
            event_type="node_resolved",
            node_id=body.node_id,
            details={"action": "manual_resolve"},
            severity="info",
        )
        return {"success": True, "node_id": body.node_id, "result": result}
    except Exception as exc:  # noqa: BLE001
        return {"success": False, "detail": str(exc)}
@app.get("/api/alerts", tags=["Alerts"])
async def get_alerts() -> list[dict[str, Any]]:
    """Return every alert detected since the process started."""
    return alerts
@app.get("/api/ledger", tags=["Ledger"])
async def get_ledger() -> dict[str, Any]:
    """Return recent ledger entries and the current integrity verification result."""
    if not ledger_store:
        return {"entries": [], "integrity": False}
    try:
        integrity = ledger_store.verify_integrity()
    except Exception:  # noqa: BLE001
        integrity = False
    return {
        "entries": ledger_store.get_recent(50),
        "integrity": integrity,
    }
@app.post("/api/copilot", tags=["Copilot"])
async def query_copilot(body: CopilotQuery) -> dict[str, Any]:
    """Query the SOP copilot with a free-text question."""
    if not copilot:
        return {"results": [], "detail": "Copilot not initialised"}
    results = copilot.query(body.query)
    return {"query": body.query, "results": results}
@app.get("/api/stats", tags=["Dashboard"])
async def get_stats() -> dict[str, Any]:
    """Return high-level summary statistics for the dashboard."""
    return _build_stats()
# ---------------------------------------------------------------------------
# WebSocket — real-time live feed
# ---------------------------------------------------------------------------
@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket) -> None:
    """Push real-time node state, new alerts, and stats to connected clients every second."""
    global _new_alert_buffer
    await ws.accept()
    try:
        while True:
            # Gather current state
            nodes_data: list[dict[str, Any]] = []
            if simulator and detector:
                for node in simulator.get_nodes():
                    anomaly = detector.detect(node)
                    nodes_data.append({**node, "anomaly": anomaly})
            # Drain the new-alert buffer (thread-safe enough for a single event-loop)
            fresh_alerts = list(_new_alert_buffer)
            _new_alert_buffer = []
            payload: dict[str, Any] = {
                "type": "update",
                "nodes": nodes_data,
                "alerts": fresh_alerts,
                "stats": _build_stats(),
            }
            await ws.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        print(f"[ws/live] connection error: {exc}")
# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
