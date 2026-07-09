from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ResearchQuery(BaseModel):
    query: str
    mode: str = "Quick Research" # Quick, Deep, Academic, Technical, News

class SourceSchema(BaseModel):
    title: str
    url: str
    content: str
    class Config:
        from_attributes = True

class ResearchResponse(BaseModel):
    query: str
    summary: str
    sources: List[SourceSchema]
    created_at: datetime
    class Config:
        from_attributes = True

class MapRequest(BaseModel):
    destination: str
    current_location: Optional[str] = None

class MapResponse(BaseModel):
    message: str
    location: Optional[dict] = None
    navigation_link: Optional[str] = None
    success: bool

class VoiceActionRequest(BaseModel):
    command: str
    phone_number: Optional[str] = None
    message: Optional[str] = None
    contact_name: Optional[str] = None

class VoiceActionResponse(BaseModel):
    action_type: str
    target: str
    link: str
    message: str
    requires_user_confirmation: bool
    privacy_note: str
    success: bool

class AIChatRequest(BaseModel):
    message: str
    history: List["AIChatMessage"] = []
    mode: str = "chat"
    provider: Optional[str] = None
    api_key: Optional[str] = None

class AIChatMessage(BaseModel):
    role: str
    content: str

class AIChatResponse(BaseModel):
    reply: str
    success: bool

class AIImageChatRequest(BaseModel):
    message: str
    image_data: str
    mime_type: str = "image/png"
    history: List[AIChatMessage] = []
    provider: Optional[str] = None
    api_key: Optional[str] = None

class TutorResearchRequest(BaseModel):
    topic: str
    level: str = "beginner"

class TutorResource(BaseModel):
    title: str
    url: str
    resource_type: str
    read_status: str
    free: bool
    summary: str
    why_useful: str

class TutorStep(BaseModel):
    order_index: int
    title: str
    goal: str
    task: str

class TutorResearchResponse(BaseModel):
    topic: str
    level: str
    resources: List[TutorResource]
    steps: List[TutorStep]
    study_plan: str
    success: bool
