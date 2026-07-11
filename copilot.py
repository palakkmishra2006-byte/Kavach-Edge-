import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
# ---------------------------------------------------------------------------
# Built‑in SOP Knowledge Base
# ---------------------------------------------------------------------------
_SOP_LIBRARY: List[Dict[str, Any]] = [
    {
        "id": "SOP-001",
        "title": "DDoS Attack Mitigation Protocol",
        "category": "Cyber Attack",
        "keywords": [
            "ddos", "distributed", "denial", "service", "flood", "traffic",
            "packets", "bandwidth", "rate-limit", "firewall", "mitigation",
        ],
        "steps": [
            "1. Activate edge firewall rate‑limiting rules to throttle inbound traffic exceeding 10 000 pps threshold.",
            "2. Enable GeoIP blocking for traffic originating outside authorised regions; log blocked IPs for forensic analysis.",
            "3. Reroute legitimate traffic through the secondary clean‑pipe ingress and verify connectivity with heartbeat probes.",
            "4. Engage traffic scrubbing on the edge gateway — divert suspicious flows to the sinkhole subnet.",
            "5. Notify the National CERT (CERT‑In) via the automated incident channel with traffic capture artefacts.",
            "6. Post‑incident: conduct packet‑capture analysis, update IDS signatures, and file a ledger entry.",
        ],
        "priority": 1,
    },
    {
        "id": "SOP-002",
        "title": "Ransomware Containment & Recovery",
        "category": "Cyber Attack",
        "keywords": [
            "ransomware", "encrypt", "malware", "containment", "isolate",
            "backup", "recovery", "memory", "lockout", "payload",
        ],
        "steps": [
            "1. Immediately isolate the affected node from the network by disabling its uplink port at the edge switch.",
            "2. Capture a forensic memory dump and disk image before any remediation to preserve evidence.",
            "3. Identify the ransomware strain from file‑extension patterns and ransom note hashes using the offline IOC database.",
            "4. Restore the node from the last verified clean backup stored on the air‑gapped recovery server.",
            "5. Rotate all credentials (SSH keys, SCADA passwords, API tokens) associated with the compromised node.",
            "6. Deploy updated endpoint‑detection signatures and re‑enable the uplink after a full scan confirms clean state.",
        ],
        "priority": 1,
    },
    {
        "id": "SOP-003",
        "title": "Sensor Spoofing Detection & Correction",
        "category": "Integrity Attack",
        "keywords": [
            "sensor", "spoofing", "spoof", "false", "reading", "calibration",
            "integrity", "oscillation", "tamper", "manipulation",
        ],
        "steps": [
            "1. Cross‑reference the suspected sensor readings against redundant sensors or neighbouring node baselines.",
            "2. Enable enhanced sensor‑validation mode — require 3‑of‑5 consensus from the sensor mesh before accepting values.",
            "3. Physically inspect the sensor hardware for signs of tampering (rewiring, firmware modification, attached devices).",
            "4. Reflash the sensor firmware from the signed golden image stored on the secure OTA server.",
            "5. Recalibrate the sensor using NIST‑traceable reference standards and log the new calibration certificate.",
        ],
        "priority": 2,
    },
    {
        "id": "SOP-004",
        "title": "Power Grid Failure Recovery",
        "category": "Infrastructure Failure",
        "keywords": [
            "grid", "failure", "power", "voltage", "blackout", "outage",
            "transformer", "current", "surge", "recovery", "generator",
        ],
        "steps": [
            "1. Activate the automatic transfer switch (ATS) to engage backup diesel generators within 10 seconds.",
            "2. Isolate the faulted feeder section using SCADA‑controlled sectionalising switches to prevent cascade.",
            "3. Deploy mobile power units to critical loads (hospitals, water pumps) within the affected zone.",
            "4. Coordinate with the State Load Despatch Centre (SLDC) to reroute supply from adjacent substations.",
            "5. Dispatch field crew with insulated tools and PPE to inspect transformers and overhead lines for faults.",
            "6. Restore load incrementally (cold‑load pickup protocol) to avoid transformer inrush current damage.",
        ],
        "priority": 1,
    },
    {
        "id": "SOP-005",
        "title": "Data Exfiltration Response",
        "category": "Cyber Attack",
        "keywords": [
            "exfiltration", "data", "leak", "breach", "transfer", "upload",
            "covert", "channel", "packets", "outbound", "theft",
        ],
        "steps": [
            "1. Immediately block all outbound traffic from the suspected node except whitelisted management channels.",
            "2. Capture a full packet trace on the node's egress interface for at least 15 minutes to identify the C2 endpoint.",
            "3. Enumerate files accessed and transmitted using the node's audit log (auditd / Windows Event Log).",
            "4. Revoke and rotate all API keys, database credentials, and TLS certificates accessible from the node.",
            "5. Notify the Data Protection Officer (DPO) and initiate the 72‑hour breach notification process per IT Act 2000.",
        ],
        "priority": 1,
    },
    {
        "id": "SOP-006",
        "title": "Network Isolation Procedure",
        "category": "Containment",
        "keywords": [
            "isolation", "network", "quarantine", "segment", "firewall",
            "vlan", "disconnect", "contain", "perimeter", "lockdown",
        ],
        "steps": [
            "1. Move the compromised node to the quarantine VLAN (VLAN 999) via the SDN controller API.",
            "2. Disable all inter‑VLAN routing rules referencing the quarantine segment.",
            "3. Enable full packet capture on the quarantine VLAN mirror port for forensic collection.",
            "4. Verify that critical services are unaffected by running automated health‑check probes on remaining nodes.",
            "5. Document the isolation action with timestamps and operator ID in the immutable ledger.",
        ],
        "priority": 2,
    },
    {
        "id": "SOP-007",
        "title": "Backup Power Activation Protocol",
        "category": "Infrastructure Failure",
        "keywords": [
            "backup", "power", "ups", "generator", "battery", "activation",
            "emergency", "supply", "diesel", "inverter",
        ],
        "steps": [
            "1. Confirm mains power loss via the building management system (BMS) and UPS status indicators.",
            "2. Verify UPS battery health — ensure remaining runtime exceeds 15 minutes for graceful generator start.",
            "3. Initiate the diesel generator auto‑start sequence; confirm stable output (400 V ± 5 %, 50 Hz ± 0.5 Hz).",
            "4. Engage the automatic transfer switch (ATS) to transition critical loads from UPS to generator bus.",
            "5. Notify facility management and update the outage dashboard with estimated restoration time.",
        ],
        "priority": 2,
    },
    {
        "id": "SOP-008",
        "title": "Water Contamination Emergency Protocol",
        "category": "Infrastructure Failure",
        "keywords": [
            "water", "contamination", "treatment", "quality", "ph",
            "chlorine", "bacterial", "purification", "emergency", "supply",
        ],
        "steps": [
            "1. Immediately shut the outlet valve on the contaminated treatment stage and activate the bypass loop.",
            "2. Collect water samples at inlet, mid‑process, and outlet points for laboratory analysis (pH, turbidity, coliform).",
            "3. Increase chlorine dosing to emergency levels (≥ 2 mg/L free residual) as a precautionary disinfection measure.",
            "4. Issue a public Do‑Not‑Use advisory via the municipal alert system for the affected distribution zone.",
            "5. Deploy mobile water tankers from reserve depots to serve the affected population within 2 hours.",
            "6. Coordinate with the State Pollution Control Board (SPCB) and file a contamination incident report.",
        ],
        "priority": 1,
    },
    {
        "id": "SOP-009",
        "title": "Traffic Signal Override & Safe‑Mode",
        "category": "Infrastructure Failure",
        "keywords": [
            "traffic", "signal", "override", "control", "intersection",
            "safe-mode", "amber", "flashing", "manual", "congestion",
        ],
        "steps": [
            "1. Switch the compromised intersection controller to fail‑safe amber‑flash mode to prevent collisions.",
            "2. Dispatch traffic police to the affected intersection(s) for manual traffic management.",
            "3. Disable remote‑access interfaces on the controller and perform a firmware integrity check.",
            "4. Restore the last‑known‑good signal plan from the offline configuration backup.",
            "5. Re‑enable automated control only after successful end‑to‑end communication verification with the TMC.",
        ],
        "priority": 2,
    },
    {
        "id": "SOP-010",
        "title": "Agricultural IoT Sensor Recalibration",
        "category": "Maintenance",
        "keywords": [
            "agriculture", "agri", "iot", "sensor", "recalibration",
            "soil", "moisture", "temperature", "drift", "calibrate",
        ],
        "steps": [
            "1. Place the sensor in the NIST‑traceable calibration environment (known temp, humidity, soil moisture).",
            "2. Record 30 consecutive readings and compute mean and standard deviation against reference values.",
            "3. If deviation exceeds ±2 %, apply the linear correction coefficients via the sensor's I²C configuration register.",
            "4. Reflash the sensor firmware from the signed OTA repository to eliminate any software‑induced drift.",
            "5. Log the recalibration event (old offsets, new offsets, reference standards used) in the asset management system.",
        ],
        "priority": 3,
    },
    {
        "id": "SOP-011",
        "title": "Coordinated Multi‑Vector Attack Response",
        "category": "Cyber Attack",
        "keywords": [
            "coordinated", "multi-vector", "advanced", "persistent", "apt",
            "combined", "attack", "simultaneous", "escalation", "response",
        ],
        "steps": [
            "1. Activate the Incident Command System (ICS) — designate Incident Commander, Communications Lead, and Tech Lead.",
            "2. Immediately isolate all nodes showing anomalous behaviour into the quarantine network segment.",
            "3. Prioritise triage by infrastructure criticality: Power → Water → Traffic → Agriculture.",
            "4. Correlate timestamps and attack vectors across nodes to identify the common kill chain and C2 infrastructure.",
            "5. Engage mutual‑aid protocols with adjacent SOCs and share IOCs through the STIX/TAXII threat‑intel feed.",
            "6. Begin phased recovery starting with the highest‑priority nodes, verifying integrity at each stage.",
        ],
        "priority": 1,
    },
]
class SOPCopilot:
    """Offline SOP retrieval co‑pilot using TF‑IDF‑style keyword scoring.
    The knowledge base is loaded in‑memory at init time and queried via
    :meth:`query` (free‑text) or :meth:`get_remediation` (structured).
    """
    def __init__(self) -> None:
        """Load the built‑in SOP library and pre‑compute IDF weights."""
        self.sops: List[Dict[str, Any]] = _SOP_LIBRARY
        # Pre‑compute inverse‑document‑frequency for all keywords
        self._idf: Dict[str, float] = self._build_idf()
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def query(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search SOPs by natural‑language *text*.
        Tokenises the query, scores each SOP using TF‑IDF‑weighted keyword
        overlap + title similarity, and returns the top *top_k* results with
        relevance scores.
        Parameters
        ----------
        text:
            Free‑form natural‑language query string.
        top_k:
            Maximum number of results to return.
        Returns
        -------
        list[dict]
            Each dict contains the full SOP plus an added ``relevance_score``
            field (float, higher is better).
        """
        tokens = self._tokenise(text)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for sop in self.sops:
            score = self._score_sop(tokens, sop)
            if score > 0:
                result = {**sop, "relevance_score": round(score, 4)}
                scored.append((score, result))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]
    def get_remediation(
        self, threat_type: str, node_type: str
    ) -> Optional[Dict[str, Any]]:
        """Return the single most relevant SOP for a classified threat.
        Parameters
        ----------
        threat_type:
            Threat classification string (e.g. ``'DDoS Attack Detected'``).
        node_type:
            Infrastructure type (e.g. ``'power_grid'``).
        Returns
        -------
        dict or None
            The best‑matching SOP dict with ``relevance_score``, or ``None``
            if nothing matches.
        """
        combined_query = f"{threat_type} {node_type.replace('_', ' ')}"
        results = self.query(combined_query, top_k=1)
        return results[0] if results else None
    def get_all_sops(self) -> List[Dict[str, Any]]:
        """Return the full SOP catalogue."""
        return list(self.sops)
    # ------------------------------------------------------------------
    # TF‑IDF scoring internals
    # ------------------------------------------------------------------
    def _build_idf(self) -> Dict[str, float]:
        """Compute IDF weights across all SOP keyword documents."""
        n_docs = len(self.sops)
        doc_freq: Counter = Counter()
        for sop in self.sops:
            unique_terms = set(sop["keywords"])
            # Also add title tokens
            unique_terms.update(self._tokenise(sop["title"]))
            for term in unique_terms:
                doc_freq[term] += 1
        idf: Dict[str, float] = {}
        for term, df in doc_freq.items():
            idf[term] = math.log((1 + n_docs) / (1 + df)) + 1  # smoothed IDF
        return idf
    def _score_sop(
        self, query_tokens: List[str], sop: Dict[str, Any]
    ) -> float:
        """Score a single SOP against the tokenised query using TF‑IDF."""
        # Build the SOP document as keyword list + title tokens
        sop_tokens = list(sop["keywords"]) + self._tokenise(sop["title"])
        sop_counter = Counter(sop_tokens)
        score = 0.0
        for qt in query_tokens:
            tf = sop_counter.get(qt, 0)
            if tf > 0:
                idf = self._idf.get(qt, 1.0)
                score += (1 + math.log(tf)) * idf
        # Bonus for priority alignment (higher priority SOPs get a small boost)
        priority_boost = max(0.0, (4 - sop.get("priority", 3)) * 0.15)
        score += priority_boost if score > 0 else 0
        return score
    @staticmethod
    def _tokenise(text: str) -> List[str]:
        """Lowercase, strip punctuation, and split *text* into tokens."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        tokens = text.split()
        # Remove very short tokens
        return [t for t in tokens if len(t) >= 2]
