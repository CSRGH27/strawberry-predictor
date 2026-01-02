from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from .database import Base
from sqlalchemy.orm import relationship

class Variety(Base):
        __tablename__ = "varieties"
        
        id = Column(Integer, primary_key=True, index=True)
        name = Column(String(100),unique=True, nullable=False)
        description = Column(String(500), nullable=True)
        harvests = relationship("HarvestRecord", back_populates="variety")
        
        
class HarvestRecord(Base):
    __tablename__ = "harvest_records"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    day_number = Column(Integer, nullable=False)      # ✅ Déjà là
    plants_nbrs = Column(Integer, nullable=False)
    kg_produced = Column(Float, nullable=False)
    year = Column(Integer, nullable=False, index=True) # ✅ Déjà là
    variety_id = Column(Integer, ForeignKey("varieties.id"))
    variety = relationship("Variety", back_populates="harvests")
        
class WeatherData(Base):
        __tablename__ = "weather_data"
        id = Column(Integer, primary_key=True, index=True)
        date = Column(Date, nullable=False, unique=True, index=True)
        # Température (impact direct sur croissance)
        temperature_max = Column(Float)  # °C
        temperature_min = Column(Float)  # °C
        temperature_mean = Column(Float)  # °C
        # Humidité (maladies, évapotranspiration)
        humidity_mean = Column(Float)  # %
        # Luminosité (photosynthèse)
        sunshine_duration = Column(Float)  # heures
        solar_radiation = Column(Float)  # MJ/m²
        # Précipitations (indicateur humidité ambiante)
        precipitation = Column(Float)  # mm
        
class PlantConfiguration(Base):
        __tablename__ = "plant_configurations" 
        id = Column(Integer, primary_key=True, index=True)
        variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=False)
        start_date = Column(Date, nullable=False, index=True)
        end_date = Column(Date, nullable=True, index=True)  # NULL = config actuelle
        plants_nbrs = Column(Integer, nullable=False)
        # Relations
        variety = relationship("Variety")
        
class Prediction(Base):                    # ← NOUVEAU
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    prediction_date = Column(DateTime, nullable=False, index=True)
    target_date = Column(Date, nullable=False, index=True)
    variety_id = Column(Integer, ForeignKey("varieties.id"), nullable=False)
    plants_nbrs = Column(Integer, nullable=False)
    kg_biological_predicted = Column(Float, nullable=False)
    kg_produced_predicted = Column(Float, nullable=False)
    harvest_fraction = Column(Float, nullable=False)
    
    variety = relationship("Variety")
    