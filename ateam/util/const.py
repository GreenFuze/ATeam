from enum import Enum

class TailType(str, Enum):
    TOKEN = "token"
    TOOL = "tool"
    WARN = "warn"
    ERROR = "error"
    TASK_START = "task.start"
    TASK_END = "task.end"

class AgentState(str, Enum):
    INIT = "init"
    REGISTERED = "registered"
    IDLE = "idle"
    BUSY = "busy"
    DISCONNECTED = "disconnected"
    SHUTDOWN = "shutdown"

DEFAULTS = {
    "HEARTBEAT_INTERVAL_SEC": 3,
    "HEARTBEAT_TTL_SEC": 10,
    "RPC_TIMEOUT_SEC": 15.0,
    "TAIL_COALESCE_MS": 50,
    "PTY_READ_IDLE_MS": 15,
    "HISTORY_MAX_BYTES": 50 * 1024 * 1024,
    "SUMMARY_TARGET_TOKENS": 400,
    "SUMMARIZE_THRESHOLD": 0.75,
    "MAX_RPC_PAYLOAD": 256 * 1024,          # 256 KiB
    "MAX_TAIL_FRAME": 8 * 1024,             # 8 KiB
}
