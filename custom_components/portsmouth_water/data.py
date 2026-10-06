"""Validate real meter readings and keep their original timestamps."""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import math

def normalize(nodes, hourly=False, now=None):
    now = now or datetime.now(timezone.utc)
    output = {}
    for node in nodes:
        if node.get("source") != "Amphio" or not node.get("startAt") or not node.get("endAt"):
            continue
        start = datetime.fromisoformat(node["startAt"])
        end = datetime.fromisoformat(node["endAt"])
        if start.tzinfo is None or end.tzinfo is None or end > now or end <= start:
            continue
        if not hourly and (start.hour or start.minute or start.second or end.hour or end.minute or end.second or not 23*3600 <= (end-start).total_seconds() <= 25*3600):
            continue
        if hourly and ((end-start).total_seconds() != 3600 or start.minute or start.second or start.microsecond):
            continue
        unit=node["unit"].lower()
        if unit not in {"m3", "l"}:
            raise ValueError("Unsupported water unit")
        value=Decimal(str(node["value"]))/(1000 if unit == "l" else 1)
        if not math.isfinite(value) or value < 0:
            raise ValueError("Invalid water consumption")
        key=str(int(start.timestamp()))
        output[key]={"start":start.isoformat(),"end":end.isoformat(),"value":str(value),"leak":any(e["label"]=="LEAK" and e["value"]=="true" for e in (node.get("metaData") or {}).get("extras") or [])}
    return output

def cumulative(history):
    total=Decimal(0)
    result=[]
    if history:
        first=history[min(history,key=int)]
        result.append({"start":datetime.fromisoformat(first["end"])-timedelta(hours=2),"state":0.0,"sum":0.0})
    for key in sorted(history,key=int):
        row=history[key]
        total+=Decimal(row["value"])
        result.append({"start":datetime.fromisoformat(row["end"])-timedelta(hours=1),"state":float(row["value"]),"sum":float(total)})
    return result
