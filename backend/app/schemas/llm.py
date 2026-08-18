from pydantic import BaseModel


class LLMModelView(BaseModel):
    id: str
    label: str
    size_bytes: int | None = None
    parameter_size: str | None = None
    quantization: str | None = None


class LLMProviderView(BaseModel):
    id: str
    label: str
    kind: str
    available: bool
    reachable: bool
    status_message: str
    models: list[LLMModelView]


class LLMProviderCatalogView(BaseModel):
    providers: list[LLMProviderView]
