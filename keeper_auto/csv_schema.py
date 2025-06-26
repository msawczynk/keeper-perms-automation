from pydantic import BaseModel, Field, validator

class PermRow(BaseModel):
    record_uid: str = Field(..., pattern=r"^[A-Za-z0-9_-]{20,}$")
    title: str
    subfolders: str

    # dynamic team columns are accepted via **data in model_config
    model_config = {"extra": "allow"}

    @validator("*", pre=True)
    def strip(cls, v):
        return v.strip() if isinstance(v, str) else v
