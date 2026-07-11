"""
Kavach-Edge Crypto Ledger
==========================
A lightweight, hash‑chained immutable ledger for recording all security events,
anomaly detections, and operator actions. Each block is cryptographically linked
to its predecessor via SHA‑256, providing tamper‑evident auditability without
requiring a full blockchain network.
Fully offline — no external services or APIs required.
"""
import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
class CryptoLedger:
    """Append‑only, hash‑chained event ledger for Kavach‑Edge.
    Every entry (block) stores:
    * ``index`` — sequential block number starting at 0 (genesis).
    * ``timestamp`` — ISO‑8601 UTC string.
    * ``event_type`` — e.g. ``'anomaly_detected'``, ``'chaos_injected'``.
    * ``node_id`` — the infrastructure node involved.
    * ``details`` — free‑form description string.
    * ``severity`` — ``'critical'``, ``'warning'``, ``'info'``, etc.
    * ``previous_hash`` — SHA‑256 hex digest of the preceding block.
    * ``hash`` — SHA‑256 hex digest of *this* block's contents + ``previous_hash``.
    """
    def __init__(self) -> None:
        """Create the ledger with a genesis block."""
        self._lock = threading.Lock()
        self._chain: List[Dict[str, Any]] = []
        self._create_genesis_block()
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def add_entry(
        self,
        event_type: str,
        node_id: str,
        details: str,
        severity: str = "info",
    ) -> Dict[str, Any]:
        """Append a new block to the chain.
        Parameters
        ----------
        event_type:
            Category of the event (e.g. ``'anomaly_detected'``).
        node_id:
            Identifier of the infrastructure node involved.
        details:
            Human‑readable description of the event.
        severity:
            One of ``'critical'``, ``'warning'``, ``'info'``, ``'normal'``.
        Returns
        -------
        dict
            The newly created block.
        """
        with self._lock:
            previous_block = self._chain[-1]
            block: Dict[str, Any] = {
                "index": previous_block["index"] + 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "node_id": node_id,
                "details": details,
                "severity": severity,
                "previous_hash": previous_block["hash"],
            }
            block["hash"] = self._compute_hash(block)
            self._chain.append(block)
            return block
    def get_chain(self) -> List[Dict[str, Any]]:
        """Return the full chain as a list of block dicts."""
        with self._lock:
            return list(self._chain)
    def get_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        """Return the last *n* blocks (most‑recent first)."""
        with self._lock:
            return list(reversed(self._chain[-n:]))
    def verify_integrity(self) -> Dict[str, Any]:
        """Walk the entire chain and verify every hash link.
        Returns
        -------
        dict
            ``is_valid`` *(bool)* — ``True`` if no tampering detected.
            ``total_blocks`` *(int)* — length of the chain.
            ``compromised_blocks`` *(list[int])* — indices of blocks whose
            recomputed hash doesn't match the stored hash or whose
            ``previous_hash`` doesn't match the prior block.
        """
        with self._lock:
            compromised: List[int] = []
            for i, block in enumerate(self._chain):
                # Verify own hash
                expected_hash = self._compute_hash(block)
                if block["hash"] != expected_hash:
                    compromised.append(i)
                    continue
                # Verify link to previous block
                if i > 0:
                    if block["previous_hash"] != self._chain[i - 1]["hash"]:
                        compromised.append(i)
            return {
                "is_valid": len(compromised) == 0,
                "total_blocks": len(self._chain),
                "compromised_blocks": compromised,
            }
    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _create_genesis_block(self) -> None:
        """Seed the chain with a deterministic genesis block."""
        genesis: Dict[str, Any] = {
            "index": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "genesis",
            "node_id": "system",
            "details": "Kavach-Edge Ledger Initialised — Genesis Block",
            "severity": "info",
            "previous_hash": "0" * 64,
        }
        genesis["hash"] = self._compute_hash(genesis)
        self._chain.append(genesis)
    @staticmethod
    def _compute_hash(block_data: Dict[str, Any]) -> str:
        """Compute SHA‑256 hex digest for a block.
        The hash is derived from a deterministic JSON serialisation of all
        block fields *except* ``hash`` itself.
        """
        block_copy = {k: v for k, v in block_data.items() if k != "hash"}
        encoded = json.dumps(block_copy, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
