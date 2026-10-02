"""The unchanged digest helper used by the structural-key control."""
import hashlib, json
from rss_trace import snapshot
def digest(value):
    return hashlib.sha256(json.dumps(snapshot(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
