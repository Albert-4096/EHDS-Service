from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 3000
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ehds_db"
    hapi_fhir_base_url: str = "http://localhost:8080/fhir"
    snowstorm_url: str = "http://localhost:8085/fhir"
    environment: str = "development"
    pdf_ocr_lang: str = "ron"
    # HP-02: column x-thresholds for demographics table (fractions of page width)
    demographics_col_thresholds: list[float] = [0.33, 0.66]
    k_anonymity_threshold: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
