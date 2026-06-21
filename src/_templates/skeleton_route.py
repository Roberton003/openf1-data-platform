"""FastAPI route template — async def, response_model, Depends."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/v1/resource", tags=["Resource"])


class ResourceResponse(BaseModel):
    """Response model for a resource."""

    id: int
    name: str


class ResourceListResponse(BaseModel):
    """List response wrapping items."""

    items: list[ResourceResponse]


def get_db():
    """Dependency that yields a database connection."""
    con = duckdb.connect(database=":memory:")
    try:
        yield con
    finally:
        con.close()


@router.get("/", response_model=ResourceListResponse)
async def list_resources(
    db=Depends(get_db),
    limit: int = 100,
) -> ResourceListResponse:
    """List all resources.

    Args:
        db: Database connection (injected).
        limit: Max results to return.

    Returns:
        ResourceListResponse with items.
    """
    rows = db.execute("SELECT id, name FROM resources LIMIT ?", [limit]).fetchdf()
    return ResourceListResponse(items=[ResourceResponse(id=r["id"], name=r["name"]) for _, r in rows.iterrows()])
