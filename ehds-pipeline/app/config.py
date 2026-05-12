from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openrouter_api_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ehds_db"
    hapi_fhir_base_url: str = "http://localhost:8080/fhir"
    environment: str = "development"
    pdf_ocr_lang: str = "ron"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
