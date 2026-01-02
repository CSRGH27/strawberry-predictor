from fastapi import APIRouter, Depends,HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime  
from .database import get_db
from .models import Variety, HarvestRecord, PlantConfiguration,Prediction    
from .schemas import(
    VarietyResponse,
    HarvestRecordResponse,
    PlantConfigurationCreate,      
    PlantConfigurationUpdate,       
    PlantConfigurationResponse,
    PredictionCreate,          
    PredictionResponse    
)

router = APIRouter(prefix="/api", tags=["API"])



@router.get("/varieties", response_model=List[VarietyResponse])
def get_varieties(db:Session = Depends(get_db)):
    """Get all varieties"""
    varieties = db.query(Variety).all()
    return varieties

@router.get("/varieties/{variety_id}", response_model=VarietyResponse)
def get_variety(variety_id: int, db: Session = Depends(get_db)):
    """Récupère une variété par son ID"""
    variety = db.query(Variety).filter(Variety.id == variety_id).first()
    if not variety:
        raise HTTPException(status_code=404, detail="Variété not found")
    return variety

@router.get("/harvests", response_model=List[HarvestRecordResponse])
def get_harvests(
    variety_id: Optional[int] = Query(None, description="Filtrer par variété"),
    year: Optional[int] = Query(None, description="Filtrer par année"),
    start_date: Optional[date] = Query(None, description="Date de début"),
    end_date: Optional[date] = Query(None, description="Date de fin"),
    limit: int = Query(100, description="Nombre maximum de résultats"),
    db: Session = Depends(get_db)
):
    """Récupère les enregistrements de récolte avec filtres optionnels"""
    query = db.query(HarvestRecord)
    
    # Filtres
    if variety_id:
        query = query.filter(HarvestRecord.variety_id == variety_id)
    
    if year:
        query = query.filter(extract('year', HarvestRecord.date) == year)
    
    if start_date:
        query = query.filter(HarvestRecord.date >= start_date)
    
    if end_date:
        query = query.filter(HarvestRecord.date <= end_date)
    
    # Tri par date décroissante
    query = query.order_by(HarvestRecord.date.desc())
    
    # Limite
    harvests = query.limit(limit).all()
    
    return harvests

@router.get("/harvests/{harvest_id}", response_model=HarvestRecordResponse)
def get_harvest(harvest_id: int, db: Session = Depends(get_db)):
    """Récupère un enregistrement de récolte par son ID"""
    harvest = db.query(HarvestRecord).filter(HarvestRecord.id == harvest_id).first()
    if not harvest:
        raise HTTPException(status_code=404, detail="Enregistrement non trouvé")
    return harvest


# ============================================================
# ROUTES STATISTIQUES
# ============================================================

@router.get("/stats/summary")
def get_stats_summary(
    variety_id: Optional[int] = Query(None, description="Filtrer par variété"),
    year: Optional[int] = Query(None, description="Filtrer par année"),
    db: Session = Depends(get_db)
):
    """Statistiques globales de production"""
    query = db.query(
        func.count(HarvestRecord.id).label('total_records'),
        func.sum(HarvestRecord.kg_produced).label('total_kg_produced'),
        func.sum(HarvestRecord.kg_declassified).label('total_kg_declassified'),
        func.sum(HarvestRecord.kg_loss).label('total_kg_loss'),
        func.avg(HarvestRecord.kg_produced).label('avg_kg_produced')
    )
    
    if variety_id:
        query = query.filter(HarvestRecord.variety_id == variety_id)
    
    if year:
        query = query.filter(extract('year', HarvestRecord.date) == year)
    
    result = query.first()
    
    return {
        "total_records": round(result.total_records or 0,3),
        "total_kg_produced": round(float(result.total_kg_produced or 0),3),
        "total_kg_declassified": round(float(result.total_kg_declassified or 0),3),
        "total_kg_loss": round(float(result.total_kg_loss or 0),3),
        "avg_kg_produced": round(float(result.avg_kg_produced or 0),3)
    }

@router.get("/stats/by-variety")
def get_stats_by_variety(
    year: Optional[int] = Query(None, description="Filtrer par année"),
    db: Session = Depends(get_db)
):
    """Statistiques par variété"""
    query = db.query(
        Variety.name,
        func.sum(HarvestRecord.kg_produced).label('total_kg_produced'),
        func.count(HarvestRecord.id).label('total_records')
    ).join(HarvestRecord)
    
    if year:
        query = query.filter(extract('year', HarvestRecord.date) == year)
    
    query = query.group_by(Variety.name).order_by(func.sum(HarvestRecord.kg_produced).desc())
    
    results = query.all()
    
    return [
        {
            "variety": r.name,
            "total_kg_produced": float(r.total_kg_produced or 0),
            "total_records": r.total_records
        }
        for r in results
    ]
    
@router.get("/plant-configs", response_model=List[PlantConfigurationResponse])
def get_plant_configurations(
    variety_id: Optional[int] = Query(None, description="Filtrer par variété"),
    active_only: bool = Query(False, description="Seulement les configurations actives"),
    db: Session = Depends(get_db)
):
    """
    Récupère les configurations de plants
    
    - active_only=True : Seulement les configs actives
    - variety_id : Filtrer par variété
    """
    query = db.query(PlantConfiguration)
    
    if variety_id:
        query = query.filter(PlantConfiguration.variety_id == variety_id)
    
    if active_only:
        today = datetime.now().date()
        query = query.filter(
            or_(
                PlantConfiguration.end_date.is_(None),
                PlantConfiguration.end_date >= today
            )
        )
    
    configs = query.order_by(
        PlantConfiguration.variety_id,
        PlantConfiguration.start_date.desc()
    ).all()
    
    return configs


@router.get("/plant-configs/current", response_model=List[PlantConfigurationResponse])
def get_current_plant_configurations(
    target_date: Optional[date] = Query(None, description="Date cible (défaut: aujourd'hui)"),
    db: Session = Depends(get_db)
):
    """
    Récupère la configuration de plants active pour une date donnée
    """
    if not target_date:
        target_date = datetime.now().date()
    
    configs = db.query(PlantConfiguration).filter(
        PlantConfiguration.start_date <= target_date,
        or_(
            PlantConfiguration.end_date.is_(None),
            PlantConfiguration.end_date >= target_date
        )
    ).all()
    
    return configs


@router.post("/plant-configs", response_model=PlantConfigurationResponse, status_code=201)
def create_plant_configuration(
    config: PlantConfigurationCreate,
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle configuration de plants
    """
    # Vérifier que la variété existe
    variety = db.query(Variety).filter(Variety.id == config.variety_id).first()
    if not variety:
        raise HTTPException(status_code=404, detail="Variété non trouvée")
    
    # Créer la configuration
    new_config = PlantConfiguration(**config.model_dump())
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return new_config


@router.put("/plant-configs/{config_id}", response_model=PlantConfigurationResponse)
def update_plant_configuration(
    config_id: int,
    config_update: PlantConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """
    Met à jour une configuration (fermer ou ajuster plants)
    """
    config = db.query(PlantConfiguration).filter(PlantConfiguration.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    
    if config_update.end_date is not None:
        config.end_date = config_update.end_date
    
    if config_update.plants_nbrs is not None:
        config.plants_nbrs = config_update.plants_nbrs
    
    db.commit()
    db.refresh(config)
    
    return config

@router.get("/predictions", response_model=List[PredictionResponse])
def get_predictions(
    variety_id: Optional[int] = Query(None, description="Filtrer par variété"),
    target_date: Optional[date] = Query(None, description="Date cible"),
    limit: int = Query(100, description="Nombre maximum de résultats"),
    db: Session = Depends(get_db)
):
    """
    Récupère les prédictions avec filtres optionnels
    """
    query = db.query(Prediction)
    
    if variety_id:
        query = query.filter(Prediction.variety_id == variety_id)
    
    if target_date:
        query = query.filter(Prediction.target_date == target_date)
    
    # Tri par date de prédiction décroissante (plus récente d'abord)
    query = query.order_by(Prediction.prediction_date.desc())
    
    predictions = query.limit(limit).all()
    
    return predictions

@router.get("/predictions/latest", response_model=List[PredictionResponse])
def get_latest_predictions(
    days: int = Query(7, description="Nombre de jours à prédire"),
    db: Session = Depends(get_db)
):
    """
    Récupère les dernières prédictions pour les N prochains jours
    (Une prédiction par jour et par variété)
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().date()
    
    # Récupérer toutes les variétés
    varieties = db.query(Variety).all()
    
    latest_predictions = []
    
    for variety in varieties:
        for day_offset in range(1, days + 1):
            target = today + timedelta(days=day_offset)
            
            # Prendre la prédiction la plus récente pour ce jour
            pred = db.query(Prediction).filter(
                Prediction.variety_id == variety.id,
                Prediction.target_date == target
            ).order_by(Prediction.prediction_date.desc()).first()
            
            if pred:
                latest_predictions.append(pred)
    
    return latest_predictions