from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.schemas.llm import LLMModelView, LLMProviderCatalogView, LLMProviderView
from backend.app.services.llm_catalog import discover_llm_providers

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/providers", response_model=LLMProviderCatalogView)
async def list_llm_providers() -> LLMProviderCatalogView:
    catalog = await discover_llm_providers(get_settings())
    return LLMProviderCatalogView(
        providers=[
            LLMProviderView(
                id=provider.id,
                label=provider.label,
                kind=provider.kind,
                available=provider.available,
                reachable=provider.reachable,
                status_message=provider.status_message,
                models=[
                    LLMModelView(
                        id=model.id,
                        label=model.label,
                        size_bytes=model.size_bytes,
                        parameter_size=model.parameter_size,
                        quantization=model.quantization,
                    )
                    for model in provider.models
                ],
            )
            for provider in catalog.providers
        ]
    )
