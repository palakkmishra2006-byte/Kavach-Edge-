import threading
import time
import random
import copy
from collections import deque
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
# ---------------------------------------------------------------------------
# Baseline configurations per infrastructure type
# ---------------------------------------------------------------------------
BASELINES: Dict[str, Dict[str, float]] = {
    "power_grid": {
        "voltage": 230.0,
        "current": 45.0,
        "packets_per_sec": 500.0,
        "temperature": 42.0,
        "cpu_load": 35.0,
        "memory_usage": 45.0,
        "anomaly_score": 0.05,
    },
    "water_treatment": {
        "voltage": 220.0,
        "current": 30.0,
        "packets_per_sec": 800.0,
        "temperature": 25.0,
        "cpu_load": 28.0,
        "memory_usage": 40.0,
        "anomaly_score": 0.04,
    },
    "traffic_control": {
        "voltage": 12.0,
        "current": 5.0,
        "packets_per_sec": 2000.0,
        "temperature": 38.0,
        "cpu_load": 55.0,
        "memory_usage": 60.0,
        "anomaly_score": 0.06,
    },
    "agri_iot": {
        "voltage": 5.0,
        "current": 0.5,
        "packets_per_sec": 150.0,
        "temperature": 35.0,
        "cpu_load": 15.0,
        "memory_usage": 25.0,
        "anomaly_score": 0.03,
    },
}
# Standard‑deviation factors for normal jitter (fraction of baseline)
JITTER_FACTOR: Dict[str, float] = {
    "voltage": 0.02,
    "current": 0.03,
    "packets_per_sec": 0.05,
    "temperature": 0.02,
    "cpu_load": 0.08,
    "memory_usage": 0.05,
    "anomaly_score": 0.02,
}
# Indian city coordinates (lat, lng)
CITY_COORDS: Dict[str, tuple] = {
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
    "Bangalore": (12.9716, 77.5946),
    "Hyderabad": (17.3850, 78.4867),
    "Jaipur": (26.9124, 75.7873),
    "Lucknow": (26.8467, 80.9462),
}
class InfrastructureSimulator:
    """Simulates 8 critical‑infrastructure edge nodes across India.
    Provides realistic telemetry generation, chaos/attack injection,
    and a rolling history buffer for dashboard consumption.
    """
    def __init__(self) -> None:
        """Initialise 8 nodes — two per infrastructure type — and start
        the background telemetry thread."""
        self._lock = threading.Lock()
        self._running = True
        # Build the node list ------------------------------------------------
        node_defs = [
            ("node-001", "Delhi Power Grid",      "power_grid",      "Delhi"),
            ("node-002", "Mumbai Water Plant",     "water_treatment", "Mumbai"),
            ("node-003", "Chennai Traffic Hub",    "traffic_control", "Chennai"),
            ("node-004", "Kolkata Agri Sensor",    "agri_iot",        "Kolkata"),
            ("node-005", "Bangalore Power Grid",   "power_grid",      "Bangalore"),
            ("node-006", "Hyderabad Water Plant",  "water_treatment", "Hyderabad"),
            ("node-007", "Jaipur Traffic Hub",     "traffic_control", "Jaipur"),
            ("node-008", "Lucknow Agri Sensor",    "agri_iot",        "Lucknow"),
        ]
        self.nodes: Dict[str, Dict[str, Any]] = {}
        for nid, name, ntype, city in node_defs:
            lat, lng = CITY_COORDS[city]
            self.nodes[nid] = {
                "id": nid,
                "name": name,
                "type": ntype,
                "status": "online",
                "city": city,
                "lat": lat,
                "lng": lng,
                "metrics": copy.deepcopy(BASELINES[ntype]),
                # Attack state
                "_attack_type": None,
                "_attack_start": None,
            }
        # Telemetry history (deque capped at 120 entries) --------------------
        self._history: deque = deque(maxlen=120)
        # Background thread ---------------------------------------------------
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Return a snapshot of all nodes with their current metrics."""
        with self._lock:
            return [self._sanitise(n) for n in self.nodes.values()]
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Return a single node by *node_id*, or ``None`` if not found."""
        with self._lock:
            node = self.nodes.get(node_id)
            return self._sanitise(node) if node else None
    def inject_chaos(self, node_id: str, attack_type: str) -> bool:
        """Put *node_id* into an attack state of *attack_type*.
        Supported attack types:
            ``ddos``, ``ransomware``, ``sensor_spoofing``,
            ``grid_failure``, ``data_exfiltration``
        Returns ``True`` if the injection succeeded.
        """
        valid_attacks = {
            "ddos", "ransomware", "sensor_spoofing",
            "grid_failure", "data_exfiltration",
        }
        if attack_type not in valid_attacks:
            return False
        with self._lock:
            node = self.nodes.get(node_id)
            if node is None:
                return False
            node["_attack_type"] = attack_type
            node["_attack_start"] = time.time()
            node["status"] = "compromised"
            return True
    def resolve_node(self, node_id: str) -> bool:
        """Clear any attack state on *node_id* and restore healthy baseline.
        Returns ``True`` if the node was found and resolved.
        """
        with self._lock:
            node = self.nodes.get(node_id)
            if node is None:
                return False
            node["_attack_type"] = None
            node["_attack_start"] = None
            node["status"] = "online"
            node["metrics"] = copy.deepcopy(BASELINES[node["type"]])
            return True
    def get_telemetry_history(self) -> List[Dict[str, Any]]:
        """Return the last 60 telemetry snapshots (≈ 60 seconds of data)."""
        with self._lock:
            history_list = list(self._history)
        return history_list[-60:]
    # ------------------------------------------------------------------
    # Telemetry update logic
    # ------------------------------------------------------------------
    def update_telemetry(self) -> None:
        """Advance telemetry for every node by one tick.
        * Healthy nodes receive small Gaussian jitter around baseline.
        * Compromised nodes have their metrics distorted based on the
          active attack type.
        """
        with self._lock:
            snapshot: Dict[str, Any] = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "nodes": {},
            }
            for nid, node in self.nodes.items():
                baseline = BASELINES[node["type"]]
                attack = node["_attack_type"]
                if attack is None:
                    # Normal jitter
                    for metric, base_val in baseline.items():
                        sigma = base_val * JITTER_FACTOR.get(metric, 0.03)
                        node["metrics"][metric] = max(0.0, random.gauss(base_val, sigma))
                else:
                    # Apply attack distortion first, then add jitter
                    self._apply_attack(node, attack, baseline)
                # Clamp anomaly_score to [0, 1]
                node["metrics"]["anomaly_score"] = max(
                    0.0, min(1.0, node["metrics"]["anomaly_score"])
                )
                snapshot["nodes"][nid] = copy.deepcopy(node["metrics"])
            self._history.append(snapshot)
    # ------------------------------------------------------------------
    # Attack distortion helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_attack(
        node: Dict[str, Any],
        attack: str,
        baseline: Dict[str, float],
    ) -> None:
        """Mutate *node* metrics in‑place to simulate an ongoing *attack*."""
        m = node["metrics"]
        if attack == "ddos":
            m["packets_per_sec"] = random.gauss(55000, 5000)
            m["cpu_load"] = random.gauss(98, 1.5)
            m["memory_usage"] = random.gauss(88, 4)
            m["voltage"] = random.gauss(baseline["voltage"], baseline["voltage"] * 0.03)
            m["current"] = random.gauss(baseline["current"] * 1.3, baseline["current"] * 0.05)
            m["temperature"] = random.gauss(baseline["temperature"] + 15, 2)
            m["anomaly_score"] = random.gauss(0.92, 0.04)
        elif attack == "ransomware":
            m["voltage"] = random.gauss(baseline["voltage"] * 0.4, 5)
            m["current"] = random.gauss(baseline["current"] * 0.2, 2)
            m["packets_per_sec"] = random.gauss(50, 20)
            m["temperature"] = random.gauss(baseline["temperature"] - 5, 2)
            m["cpu_load"] = random.gauss(12, 3)
            m["memory_usage"] = random.gauss(97, 1.5)
            m["anomaly_score"] = random.gauss(0.95, 0.03)
        elif attack == "sensor_spoofing":
            for metric in ("voltage", "current", "temperature", "packets_per_sec"):
                oscillation = baseline[metric] * random.uniform(-0.6, 0.6)
                m[metric] = baseline[metric] + oscillation
            m["cpu_load"] = random.gauss(baseline["cpu_load"] + 10, 5)
            m["memory_usage"] = random.gauss(baseline["memory_usage"] + 8, 3)
            m["anomaly_score"] = random.gauss(0.78, 0.08)
        elif attack == "grid_failure":
            m["voltage"] = random.gauss(3.0, 2.0)
            m["current"] = random.gauss(baseline["current"] * 3.5, baseline["current"] * 0.5)
            m["packets_per_sec"] = random.gauss(baseline["packets_per_sec"] * 0.3, 30)
            m["temperature"] = random.gauss(baseline["temperature"] + 25, 3)
            m["cpu_load"] = random.gauss(75, 8)
            m["memory_usage"] = random.gauss(80, 5)
            m["anomaly_score"] = random.gauss(0.97, 0.02)
        elif attack == "data_exfiltration":
            m["packets_per_sec"] = random.gauss(35000, 4000)
            m["cpu_load"] = random.gauss(65, 6)
            m["memory_usage"] = random.gauss(72, 4)
            m["voltage"] = random.gauss(baseline["voltage"], baseline["voltage"] * 0.02)
            m["current"] = random.gauss(baseline["current"], baseline["current"] * 0.03)
            m["temperature"] = random.gauss(baseline["temperature"] + 5, 2)
            m["anomaly_score"] = random.gauss(0.85, 0.05)
        # Ensure no negative values
        for k in m:
            m[k] = max(0.0, m[k])
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _sanitise(node: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of *node* without private ``_``‑prefixed keys."""
        return {k: v for k, v in node.items() if not k.startswith("_")}
    def _run_loop(self) -> None:
        """Background loop — calls :meth:`update_telemetry` every second."""
        while self._running:
            self.update_telemetry()
            time.sleep(1.0)
    def stop(self) -> None:
        """Gracefully stop the background telemetry thread."""
        self._running = False
        self._thread.join(timeout=3)
