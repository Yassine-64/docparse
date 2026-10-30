from __future__ import annotations


def serve(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    """Run the HTTP API (requires `docparse[api]`)."""
    import uvicorn

    uvicorn.run(
        "docparse.interfaces.api.app:create_app", host=host, port=port, reload=reload, factory=True
    )
