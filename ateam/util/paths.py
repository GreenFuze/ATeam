from pathlib import Path

class SandboxViolation(Exception): ...

def expand_user_vars(path: str) -> str:
    return str(Path(path).expanduser())

def resolve_within(base: str, candidate: str) -> str:
    base_p = Path(base).resolve(strict=True)
    cand_p = (base_p / candidate).resolve(strict=True) if not Path(candidate).is_absolute() else Path(candidate).resolve(strict=True)
    try:
        cand_p.relative_to(base_p)
    except ValueError as e:
        raise SandboxViolation(f"path escapes sandbox: {cand_p} !~ {base_p}") from e
    return str(cand_p)
