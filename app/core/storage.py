from app.core.config import settings


def build_resource_url(path: str) -> str:
    cdn_domain = "https://cdn.valbara.top" if settings.ENV.lower() == "prod" else "https://cdn-dev.valbara.top"
    return f"{cdn_domain}{path}"