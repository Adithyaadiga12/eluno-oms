from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    resend_api_key: str = ""
    alert_email_to: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"
    alert_whatsapp_to: str = ""
    app_env: str = "dev"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
