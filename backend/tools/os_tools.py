import os
from typing import Optional


def get_environment_variable(name: str, default: Optional[str] = None) -> str:
    """
    Get the value of an environment variable.

    Parameters
    ----------
    name : str
        The name of the environment variable to read (case-sensitive on POSIX).
    default : Optional[str]
        Optional default to return if the variable is not set. If not provided
        and the variable is missing, an exception is raised (fail-fast).

    Returns
    -------
    str
        The environment variable value or the provided default.

    Raises
    ------
    ValueError
        If the variable is not set and no default is provided.
    """
    if name in os.environ:
        return os.environ[name]
    if default is not None:
        return default
    raise ValueError(f"Environment variable '{name}' is not set and no default was provided")


def get_current_directory() -> str:
    """
    Get the current working directory for the running process.

    Returns
    -------
    str
        Absolute path of the current working directory.
    """
    return os.getcwd()


def read_file(path: str, encoding: str = "utf-8") -> str:
    """
    Read and return the full contents of a text file.

    Parameters
    ----------
    path : str
        Absolute or relative path to the file.
    encoding : str
        Text encoding to use when reading the file (default: utf-8).

    Returns
    -------
    str
        File contents as a string.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the specified path.
    UnicodeDecodeError
        If the file cannot be decoded using the specified encoding.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding=encoding) as f:
        return f.read()


