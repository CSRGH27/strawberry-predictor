import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime
from .database import SessionLocal, engine
from .models import Variety, HarvestRecord, Base

Base.metadata.create_all(bind=engine)

def import_varieties(db: Session):
    """Importe les variétés dans la base de données"""
    varieties_names = ["Clery", "Ciflorette", "Manon", "Dream"]
    for name in varieties_names:
        # Vérifie si la variété existe déjà
        existing = db.query(Variety).filter(Variety.name == name).first()
        if not existing:
            variety = Variety(name=name)
            db.add(variety)
            print(f"✅ Variété '{name}' ajoutée")
        else:
            print(f"⏭️  Variété '{name}' existe déjà")
            
    db.commit()
    print("\n✅ Import des variétés terminé\n")
    
def import_harvest_data(db: Session, excel_file: str):
    """Importe les données de récolte depuis le fichier Excel"""
    
    # Lire toutes les feuilles Excel
    excel_data = pd.ExcelFile(excel_file)
    variety_sheets = ["Clery", "Ciflorette", "Manon", "Dream"]
    
    total_imported = 0
    
    for sheet_name in variety_sheets:
        if sheet_name not in excel_data.sheet_names:
            print(f"⚠️  Feuille '{sheet_name}' non trouvée")
            continue
        
        print(f"📊 Import de '{sheet_name}'...")
        
        # Récupérer la variété
        variety = db.query(Variety).filter(Variety.name == sheet_name).first()
        if not variety:
            print(f"❌ Variété '{sheet_name}' non trouvée en base")
            continue
        
        # Lire la feuille
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Importer chaque ligne
        for _, row in df.iterrows():
            # Vérifier si l'enregistrement existe déjà
            existing = db.query(HarvestRecord).filter(
                HarvestRecord.variety_id == variety.id,
                HarvestRecord.date == pd.to_datetime(row['Date']).date()
            ).first()
            
            if existing:
                continue  # On saute les doublons
            
            # Créer l'enregistrement
            harvest = HarvestRecord(
                date=pd.to_datetime(row['Date']).date(),
                day_number=int(row['Jour']) if pd.notna(row['Jour']) else 1,  # ✅ AJOUTÉ
                plants_nbrs=int(row['Plants']) if pd.notna(row['Plants']) else 0,
                kg_produced=float(row['Kg produits']) if pd.notna(row['Kg produits']) else 0.0,
                year=int(row['Année']),  # ✅ CORRIGÉ (virgule manquante)
                variety_id=variety.id
            )
            db.add(harvest)
            total_imported += 1
        
        db.commit()
        print(f"✅ '{sheet_name}' importé")
    
    print(f"\n🎉 Import terminé : {total_imported} enregistrements ajoutés\n")
    
def main():
    """Fonction principale d'import"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🍓 IMPORT DES DONNÉES DE RÉCOLTE")
        print("="*60 + "\n")
        
        # 1. Importer les variétés
        import_varieties(db)
        
        # 2. Importer les données de récolte
        excel_file = "/app/data/data.xlsx"
        import_harvest_data(db, excel_file)
        
        # 3. Afficher les statistiques
        total_varieties = db.query(Variety).count()
        total_harvests = db.query(HarvestRecord).count()
        
        print("="*60)
        print(f"📊 STATISTIQUES")
        print("="*60)
        print(f"Variétés : {total_varieties}")
        print(f"Enregistrements de récolte : {total_harvests}")
        print("="*60 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()