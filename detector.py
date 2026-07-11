
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Any, List, Tuple
# ---------------------------------------------------------------------------
# Baseline references (mirrored from simulator for deviation analysis)
# ---------------------------------------------------------------------------
BASELINES: Dict[str, Dict[str, float]] = {
    "power_grid": {
        "voltage": 230.0,
        "current": 45.0,
        "packets_per_sec": 500.0,
        "temperature": 42.0,
        "cpu_load": 35.0,
        "memory_usage": 45.0,
    },
    "water_treatment": {
        "voltage": 220.0,
        "current": 30.0,
        "packets_per_sec": 800.0,
        "temperature": 25.0,
        "cpu_load": 28.0,
        "memory_usage": 40.0,
    },
    "traffic_control": {
        "voltage": 12.0,
        "current": 5.0,
        "packets_per_sec": 2000.0,
        "temperature": 38.0,
        "cpu_load": 55.0,
        "memory_usage": 60.0,
    },
    "agri_iot": {
        "voltage": 5.0,
        "current": 0.5,
        "packets_per_sec": 150.0,
        "temperature": 35.0,
        "cpu_load": 15.0,
        "memory_usage": 25.0,
    },
}
FEATURE_KEYS: List[str] = [
    "voltage", "current", "packets_per_sec",
    "temperature", "cpu_load", "memory_usage",
]
class AnomalyDetector:
    """Edge‑AI anomaly detector backed by an Isolation Forest.
    The model is trained once on synthetic *normal* data during
    initialisation and then used for single‑sample prediction via
    :meth:`detect`.
    """
    def __init__(self) -> None:
        """Train an Isolation Forest on 500 synthetic normal samples per
        infrastructure type (2 000 total)."""
        self.model = IsolationForest(
            contamination=0.1,
            n_estimators=100,
            random_state=42,
        )
        training_data = self._generate_training_data()
        self.model.fit(training_data)
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run anomaly detection on a single node's current metrics.
        Parameters
        ----------
        node_data:
            A node dict as returned by :pymethod:`InfrastructureSimulator.get_node`.
            Must contain a ``metrics`` sub‑dict with the standard 6 feature keys.
        Returns
        -------
        dict
            ``is_anomaly`` *(bool)* — whether the sample is anomalous.
            ``anomaly_score`` *(float)* — raw score from the model (negative =
            more anomalous).
            ``severity`` *(str)* — ``'critical'``, ``'warning'``, or ``'normal'``.
            ``confidence`` *(float)* — confidence value in ``[0, 1]``.
        """
        features = self._extract_features(node_data)
        feature_array = np.array(features).reshape(1, -1)
        prediction: int = int(self.model.predict(feature_array)[0])
        raw_score: float = float(self.model.decision_function(feature_array)[0])
        is_anomaly = prediction == -1
        # Map raw_score to a 0‑1 confidence:
        #   score << 0  → high confidence anomaly (→ 1.0)
        #   score >> 0  → high confidence normal   (→ 1.0)
        confidence = min(1.0, abs(raw_score) * 2.5)
        # Severity based on score thresholds
        if raw_score < -0.15:
            severity = "critical"
        elif raw_score < 0.0:
            severity = "warning"
        else:
            severity = "normal"
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(raw_score, 4),
            "severity": severity,
            "confidence": round(confidence, 4),
        }
    def get_threat_classification(
        self,
        node_data: Dict[str, Any],
        anomaly_result: Dict[str, Any],
    ) -> str:
        """Classify the probable threat type from metric deviations.
        Compares current metrics against the node‑type baseline and uses
        a rule‑based heuristic on the *most deviated* features to return
        a human‑readable threat classification string.
        Parameters
        ----------
        node_data:
            The node dict (must include ``type`` and ``metrics``).
        anomaly_result:
            The dict returned by :meth:`detect`.
        Returns
        -------
        str
            One of ``'DDoS Attack Detected'``, ``'Ransomware Signature'``,
            ``'Sensor Spoofing'``, ``'Grid Failure'``,
            ``'Data Exfiltration'``, or ``'Unknown Anomaly'``.
        """
        if not anomaly_result.get("is_anomaly"):
            return "Normal — No Threat"
        node_type: str = node_data.get("type", "power_grid")
        baseline = BASELINES.get(node_type, BASELINES["power_grid"])
        metrics: Dict[str, float] = node_data.get("metrics", {})
        # Compute normalised deviations
        deviations: Dict[str, float] = {}
        for key in FEATURE_KEYS:
            base_val = baseline.get(key, 1.0)
            cur_val = metrics.get(key, base_val)
            if base_val == 0:
                deviations[key] = abs(cur_val)
            else:
                deviations[key] = (cur_val - base_val) / base_val
        pps_dev = deviations.get("packets_per_sec", 0)
        cpu_dev = deviations.get("cpu_load", 0)
        mem_dev = deviations.get("memory_usage", 0)
        volt_dev = deviations.get("voltage", 0)
        cur_dev = deviations.get("current", 0)
        temp_dev = deviations.get("temperature", 0)
        # ---------- DDoS: packets spike enormously, cpu near max ----------
        if pps_dev > 5.0 and cpu_dev > 1.0:
            return "DDoS Attack Detected"
        # ---------- Ransomware: memory spikes, most other metrics drop ----
        if mem_dev > 0.8 and cpu_dev < -0.3 and pps_dev < -0.5:
            return "Ransomware Signature"
        # ---------- Grid Failure: voltage collapses, current spikes -------
        if volt_dev < -0.7 and cur_dev > 1.0:
            return "Grid Failure"
        # ---------- Data Exfiltration: packets high, cpu moderate ---------
        if pps_dev > 3.0 and 0.2 < cpu_dev < 1.5:
            return "Data Exfiltration"
        # ---------- Sensor Spoofing: wide oscillation on multiple metrics -
        oscillation_count = sum(
            1 for k in ("voltage", "current", "temperature", "packets_per_sec")
            if abs(deviations.get(k, 0)) > 0.25
        )
        if oscillation_count >= 3:
            return "Sensor Spoofing"
        return "Unknown Anomaly"
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_features(node_data: Dict[str, Any]) -> List[float]:
        """Pull the 6 feature values from a node dict's ``metrics``."""
        metrics = node_data.get("metrics", {})
        return [metrics.get(k, 0.0) for k in FEATURE_KEYS]
    @staticmethod
    def _generate_training_data() -> np.ndarray:
        """Create 500 synthetic *normal* samples per infrastructure type.
        Each sample is drawn from a Gaussian centred on the baseline with
        small standard deviations to represent healthy fluctuation.
        """
        rng = np.random.RandomState(42)
        samples: List[np.ndarray] = []
        jitter_fracs = {
            "voltage": 0.02,
            "current": 0.03,
            "packets_per_sec": 0.05,
            "temperature": 0.02,
            "cpu_load": 0.08,
            "memory_usage": 0.05,
        }
        for _node_type, baseline in BASELINES.items():
            for _ in range(500):
                row = []
                for key in FEATURE_KEYS:
                    base = baseline[key]
                    sigma = base * jitter_fracs.get(key, 0.03)
                    row.append(max(0.0, rng.normal(base, sigma)))
                samples.append(np.array(row))
        return np.array(samples)