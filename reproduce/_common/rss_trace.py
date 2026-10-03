"""Serialize the native objects consumed by the checker and structural-key digest."""
import math
import numpy as np


def snapshot(value):
    seen = {}

    def encode(x):
        if isinstance(x, np.generic):
            return encode(x.item())
        if x is None or isinstance(x, (str, bool, int)):
            return x
        if isinstance(x, float):
            return x if math.isfinite(x) else {"nonfinite": str(x)}
        if isinstance(x, np.ndarray):
            return {"ndarray": encode(x.tolist()), "dtype": str(x.dtype), "shape": list(x.shape)}
        if isinstance(x, (list, tuple)):
            return [encode(y) for y in x]
        if isinstance(x, dict):
            return {str(k): encode(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
        if id(x) in seen:
            return {"ref": seen[id(x)]}
        key = len(seen)
        seen[id(x)] = key
        fields = getattr(type(x), "__slots__", ())
        if not fields:
            raise TypeError("Unsupported history type: " + type(x).__name__)
        return {"id": key, "type": type(x).__name__, "fields": {k: encode(getattr(x, k)) for k in fields}}

    return encode(value)

