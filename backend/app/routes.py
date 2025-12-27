from fastapi import APIRouter, Depends,HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date
from .database import get_db
from .models import Variety, HarvestRecord
from .schemas import(
    VarietyResponse,
    HarvestRecordResponse,
    VarietyCreate,
    HarvestRecordCreate
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