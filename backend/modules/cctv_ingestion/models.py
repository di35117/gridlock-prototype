from pydantic import BaseModel, Field

class CCTVResponse(BaseModel):
    status: str = Field(..., description="Status of the ingestion")
    message: str = Field(..., description="Confirmation message")