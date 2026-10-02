from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./ps5.db"

    JWT_SECRET_KEY: str = "insecure_dev_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    FIELD_ENCRYPTION_KEY: str = ""

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "ps5-wound-images"
    S3_REGION: str = "us-east-1"

    STORAGE_BACKEND: str = "local"
    LOCAL_UPLOAD_DIR: str = "uploads"

    CLASSIFIER_ONNX_PATH: str = "Ml_training/models/onnx/wound_classifier_phase1_final.onnx"
    CLASSIFIER_INPUT_SIZE: int = 224
    CLASSIFIER_CLASS_NAMES: str = "mild_concern,normal,urgent"

    SEGMENTATION_BACKEND: str = "medsam"
    MEDSAM_CHECKPOINT_PATH: str = "Ml_training/models/medsam/medsam_vit_b.pth"
    SEGMENTATION_PX_PER_CM: float = 40.0

    WHISPER_MODEL_SIZE: str = "tiny"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    PIPER_EXECUTABLE: str = ""
    PIPER_MODEL_PATH: str = ""

    CONFIDENCE_THRESHOLD: float = 0.7


settings = Settings()
