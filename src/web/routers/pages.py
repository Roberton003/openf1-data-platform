import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Setup templates directory relative to this file
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../templates"))
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """
    Renders the main F1 telemetry dashboard.
    """
    return templates.TemplateResponse(request, "index.html")


@router.get("/observabilidade", response_class=HTMLResponse)
async def get_observability(request: Request):
    """
    Renders the data pipeline observability dashboard.
    """
    return templates.TemplateResponse(request, "observabilidade.html")
