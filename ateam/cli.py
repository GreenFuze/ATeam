import asyncio
import typer
from typing import Optional
from ateam.console.app import ConsoleApp
from ateam.agent.main import AgentApp
from ateam.util.types import Result, ErrorInfo

app = typer.Typer(add_completion=False, help="ATeam CLI - Console and Agent runtime")

@app.command()
def console(redis: str = typer.Option("redis://127.0.0.1:6379/0", "--redis"),
            no_ui: bool = typer.Option(False, "--no-ui", help="Disable panes"),
            panes: bool = typer.Option(False, "--panes", help="Force panes UI"),
            takeover: bool = typer.Option(False, "--takeover", help="Enable takeover mode for owned agents"),
            grace_timeout: int = typer.Option(30, "--grace-timeout", help="Grace timeout for takeover (seconds)"),
            log_level: str = typer.Option("info", "--log-level")):
    """Run the central Console."""
    # TODO(tsvi): wire logging level
    use_panes = (not no_ui) and panes
    app_ = ConsoleApp(redis_url=redis, use_panes=use_panes, takeover=takeover, grace_timeout=grace_timeout)
    try:
        app_.run()
    except KeyboardInterrupt:
        pass
    finally:
        app_.shutdown()

@app.command()
def agent(redis: Optional[str] = typer.Option(None, "--redis", help="Redis URL for distributed mode (required unless --standalone)"),
          standalone: bool = typer.Option(False, "--standalone", help="Run in standalone mode without Redis connection"),
          cwd: Optional[str] = typer.Option(None, "--cwd"),
          name: Optional[str] = typer.Option(None, "--name"),
          project: Optional[str] = typer.Option(None, "--project"),
          log_level: str = typer.Option("info", "--log-level")):
    """Run an Agent process with local REPL.
    
    The agent can run in two modes:
    - Distributed mode (default): Requires Redis for multi-agent coordination
    - Standalone mode: Runs locally without Redis, all local features work normally
    """
    # Validate that either --redis or --standalone is provided
    if not standalone and redis is None:
        # Check environment variable
        import os
        redis = os.environ.get("ATEAM_REDIS_URL", "redis://127.0.0.1:6379/0")
        if redis == "":
            typer.echo("[error] Either --redis URL or --standalone must be specified")
            typer.echo("Use --standalone to run without Redis, or --redis to specify Redis URL")
            raise typer.Exit(code=1)
    
    if standalone and redis is not None:
        typer.echo("[error] Cannot use both --standalone and --redis")
        typer.echo("Use --standalone for local mode, or --redis for distributed mode")
        raise typer.Exit(code=1)
    
    # Set redis_url to None for standalone mode
    redis_url = None if standalone else redis
    
    # TODO(tsvi): support overrides for cwd/name/project
    app_ = AgentApp(redis_url=redis_url, cwd=cwd or ".", name_override=name or "", project_override=project or "")
    
    # Bootstrap and run the agent
    async def run_agent():
        bootstrap_result = await app_.bootstrap()
        if not bootstrap_result.ok:
            return bootstrap_result
        
        try:
            return await app_.run()
        except KeyboardInterrupt:
            await app_.shutdown()
            return Result(ok=True)
        except Exception as e:
            await app_.shutdown()
            return Result(ok=False, error=ErrorInfo("agent.run_failed", str(e)))
    
    res = asyncio.run(run_agent())
    if not res.ok:
        typer.echo(f"[error] {res.error.code}: {res.error.message}")
        
        # Handle specific error codes with appropriate exit codes
        if res.error.code == "agent.duplicate":
            raise typer.Exit(code=11)
        else:
            raise typer.Exit(code=1)

def main():
    app()

if __name__ == "__main__":
    main()
