from pydantic import BaseModel, Field, ConfigDict
from typing import Dict

class OSINTRequest(BaseModel):
    # 'alias="text"' tells FastAPI to map an incoming "text" key to this "raw_text" field
    # 'populate_by_name=True' allows you to use either key name in your JSON
    raw_text: str = Field(
        ..., 
        alias="text", 
        description="Unstructured text from news, social media, or police radio"
    )
    source: str = Field("Twitter/News", description="Where the intel came from")

    model_config = ConfigDict(populate_by_name=True)

class OSINTResponse(BaseModel):
    status: str
    extracted_data: Dict  # Explicitly using Dict is safer than 'dict' for Pydantic
    forecasted_risk: float
    registration_message: str