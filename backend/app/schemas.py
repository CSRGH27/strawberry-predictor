from pydantic import BaseModel
from datetime import date
from typing import Optional


class VarietyBase(BaseModel):
    name: str
    description: Optional[str] = None

class VarietyCreate(VarietyBase):
    pass

class VarietyResponse(VarietyBase):
    id: int
    
    class Config:
        from_attributes = True

class HarvestRecordBase(BaseModel):
    date: date
    plants_nbrs: int = 0
    kg_produced: float = 0.0


class HarvestRecordCreate(HarvestRecordBase):
    variety_id: int

class HarvestRecordResponse(HarvestRecordBase):
    id: int
    variety_id: int
    variety: VarietyResponse
    
    class Config:
        from_attributes = True