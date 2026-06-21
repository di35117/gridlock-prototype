from pydantic import BaseModel, Field

class OSINTRequest(BaseModel):
    raw_text: str = Field(..., description="Unstructured text from news, social media, or police radio")
    source: str = Field("Twitter/News", description="Where the intel came from")

class OSINTResponse(BaseModel):
    status: str
    extracted_data: dict  # Will now include latitude and longitude
    forecasted_risk: float
    registration_message: str