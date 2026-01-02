from pydantic import BaseModel
from datetime import date, datetime
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
        
class PlantConfigurationBase(BaseModel):
    variety_id: int
    start_date: date
    end_date: Optional[date] = None
    plants_nbrs: int

class PlantConfigurationCreate(PlantConfigurationBase):
    pass

class PlantConfigurationUpdate(BaseModel):
    end_date: Optional[date] = None
    plants_nbrs: Optional[int] = None

class PlantConfigurationResponse(PlantConfigurationBase):
    id: int
    variety: VarietyResponse
    
    class Config:
        from_attributes = True
        
class PredictionBase(BaseModel):
    prediction_date: datetime
    target_date: date
    variety_id: int
    plants_nbrs: int
    kg_biological_predicted: float
    kg_produced_predicted: float
    harvest_fraction: float

class PredictionCreate(PredictionBase):
    pass

class PredictionResponse(PredictionBase):
    id: int
    variety: VarietyResponse
    
    class Config:
        from_attributes = True