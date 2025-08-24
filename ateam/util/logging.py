import json, sys, time, os
from .secrets import redact_dict

def log(lvl: str, where: str, msg: str, **kw):
    # Redact sensitive information from log data
    redacted_kw = redact_dict(kw)
    
    if os.getenv("ATEAM_LOG_FORMAT","json") == "json":
        rec = {"ts": time.time(), "lvl": lvl, "where": where, "msg": msg}
        rec.update(redacted_kw)
        sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
    else:
        # Redact sensitive information from message as well
        redacted_msg = redact_dict({"msg": msg})["msg"]
        sys.stdout.write(f"[{lvl}] {where}: {redacted_msg} {redacted_kw}\n")
    sys.stdout.flush()
