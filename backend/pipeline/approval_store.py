from typing import Any, Dict

# Hackathon in-memory store.
# Replace with DB/Redis for production.
APPROVAL_STORE: Dict[str, Dict[str, Any]] = {}