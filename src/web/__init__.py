"""FastAPI layer for exposing analysis results."""

from src.web.api import create_app
from src.web.service import AnalysisWebService

__all__ = ["AnalysisWebService", "create_app"]
