import pandas as pd
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import HarvestRecord, WeatherData, Variety

def create_ml_dataset():
    """
    Crée le dataset pour le Machine Learning
    VERSION SIMPLIFIÉE - Basée sur la nouvelle structure de données
    """
    
    db = SessionLocal()
    
    try:
        print("\n" + "="*70)
        print("🤖 CRÉATION DU DATASET ML (Version simplifiée)")
        print("="*70 + "\n")
        
        # ============================================================
        # ÉTAPE 1 : Récupérer les récoltes
        # ============================================================
        print("📊 Étape 1/6 : Récupération des données de récolte...")
        
        harvests_query = db.query(
            HarvestRecord.date,
            HarvestRecord.day_number,
            HarvestRecord.plants_nbrs,
            HarvestRecord.kg_produced,
            HarvestRecord.year,
            Variety.name.label('variety')
        ).join(Variety)
        
        harvests_df = pd.read_sql(harvests_query.statement, db.bind)
        
        print(f"   ✅ {len(harvests_df)} enregistrements de récolte récupérés")
        print(f"   📋 Variétés : {harvests_df['variety'].unique().tolist()}")
        
        # ============================================================
        # ÉTAPE 2 : Récupérer la météo
        # ============================================================
        print("\n🌤️  Étape 2/6 : Récupération des données météo...")
        
        weather_query = db.query(WeatherData)
        weather_df = pd.read_sql(weather_query.statement, db.bind)
        
        print(f"   ✅ {len(weather_df)} enregistrements météo récupérés")
        
        # ============================================================
        # ÉTAPE 3 : Fusionner récoltes + météo
        # ============================================================
        print("\n🔗 Étape 3/6 : Fusion des données...")
        
        harvests_df['date'] = pd.to_datetime(harvests_df['date'])
        weather_df['date'] = pd.to_datetime(weather_df['date'])
        
        dataset = pd.merge(harvests_df, weather_df, on='date', how='left')
        
        print(f"   ✅ {len(dataset)} lignes après fusion")
        
        # ============================================================
        # ÉTAPE 4 : Calcul des moyennes glissantes (7 jours)
        # ============================================================
        print("\n📈 Étape 4/6 : Calcul des moyennes glissantes...")
        
        dataset = dataset.sort_values(['variety', 'date'])
        
        for variety in dataset['variety'].unique():
            mask = dataset['variety'] == variety
            
            # Moyennes météo sur 7 jours
            dataset.loc[mask, 'temp_mean_7d'] = dataset.loc[mask, 'temperature_mean'].rolling(7, min_periods=1).mean()
            dataset.loc[mask, 'humidity_mean_7d'] = dataset.loc[mask, 'humidity_mean'].rolling(7, min_periods=1).mean()
            dataset.loc[mask, 'precipitation_7d_sum'] = dataset.loc[mask, 'precipitation'].rolling(7, min_periods=1).sum()
            dataset.loc[mask, 'sunshine_7d_sum'] = dataset.loc[mask, 'sunshine_duration'].rolling(7, min_periods=1).sum()
            dataset.loc[mask, 'solar_radiation_7d_mean'] = dataset.loc[mask, 'solar_radiation'].rolling(7, min_periods=1).mean()
            
            # Production observée des 7 derniers jours
            dataset.loc[mask, 'kg_produced_7d_mean'] = dataset.loc[mask, 'kg_produced'].rolling(7, min_periods=1).mean()
            dataset.loc[mask, 'kg_produced_7d_sum'] = dataset.loc[mask, 'kg_produced'].rolling(7, min_periods=1).sum()
            
            # Production du jour précédent
            dataset.loc[mask, 'kg_produced_prev_day'] = dataset.loc[mask, 'kg_produced'].shift(1)
        
        print(f"   ✅ Moyennes glissantes calculées pour {len(dataset['variety'].unique())} variétés")
        
        # ============================================================
        # ÉTAPE 5 : Calculer la capacité biologique
        # ============================================================
        print("\n🌱 Étape 5/7 : Calcul de la capacité biologique...")
        
        # Créer d'abord day_of_week pour déterminer la fraction récoltée
        dataset['day_of_week'] = pd.to_datetime(dataset['date']).dt.dayofweek
        
        # Définir la fraction de plants récoltés par jour de semaine
        # 0=Lundi, 1=Mardi, 2=Mercredi, 3=Jeudi, 4=Vendredi, 5=Samedi, 6=Dimanche
        harvest_fraction = {
            0: 1/3,  # Lundi
            1: 1/3,  # Mardi
            2: 1/3,  # Mercredi
            3: 1/2,  # Jeudi
            4: 1/2,  # Vendredi
            5: 1/2,  # Samedi
            6: 0     # Dimanche (sera filtré plus tard)
        }
        
        # Appliquer la fraction correspondante
        dataset['harvest_fraction'] = dataset['day_of_week'].map(harvest_fraction)
        
        # Calculer la production biologique (capacité réelle de tous les plants)
        dataset['kg_biological'] = dataset['kg_produced'] / dataset['harvest_fraction']
        
        # Pour éviter division par zéro sur les dimanches (avant filtrage)
        dataset.loc[dataset['harvest_fraction'] == 0, 'kg_biological'] = 0
        
        print(f"   ✅ Capacité biologique calculée")
        print(f"   💡 Lun-Mar-Mer: kg_produced × 3")
        print(f"   💡 Jeu-Ven-Sam: kg_produced × 2")
        
        # Calculer les moyennes glissantes de la capacité biologique
        print(f"   🌱 Calcul des tendances de capacité biologique...")
        
        for variety in dataset['variety'].unique():
            mask = dataset['variety'] == variety
            
            # Moyennes glissantes de la capacité biologique
            dataset.loc[mask, 'kg_biological_7d_mean'] = dataset.loc[mask, 'kg_biological'].rolling(7, min_periods=1).mean()
            dataset.loc[mask, 'kg_biological_14d_mean'] = dataset.loc[mask, 'kg_biological'].rolling(14, min_periods=1).mean()
            dataset.loc[mask, 'kg_biological_prev_day'] = dataset.loc[mask, 'kg_biological'].shift(1)
        
        print(f"   ✅ Tendances biologiques calculées")
        
        # ============================================================
        # ÉTAPE 6 : Créer des features temporelles
        # ============================================================
        print("\n🕐 Étape 6/7 : Création des features temporelles...")
        
        # Extraire des informations de la date
        dataset['month'] = dataset['date'].dt.month
        dataset['week_of_year'] = dataset['date'].dt.isocalendar().week
        dataset['day_of_year'] = dataset['date'].dt.dayofyear
        
        # Jours depuis le début de la saison (pour chaque variété/année)
        for variety in dataset['variety'].unique():
            for year in dataset['year'].unique():
                mask = (dataset['variety'] == variety) & (dataset['year'] == year)
                if mask.sum() > 0:
                    first_date = dataset.loc[mask, 'date'].min()
                    dataset.loc[mask, 'days_since_season_start'] = (dataset.loc[mask, 'date'] - first_date).dt.days
        
        # Delta de température (changement par rapport à la moyenne 7j)
        dataset['temp_delta'] = dataset['temperature_mean'] - dataset['temp_mean_7d']
        
        # Production par plant (rendement)
        dataset['kg_per_plant'] = dataset['kg_produced'] / (dataset['plants_nbrs'] + 1)
        
        print(f"   ✅ Features temporelles créées")
        
        # ============================================================
        # ÉTAPE 7 : Filtrer les dimanches et sauvegarder
        # ============================================================
        print("\n💾 Étape 7/7 : Filtrage et sauvegarde...")
        
        total_before = len(dataset)
        
        # Filtrer les dimanches (day_of_week = 6)
        dataset = dataset[dataset['day_of_week'] != 6]
        
        total_after = len(dataset)
        removed = total_before - total_after
        
        print(f"   ✅ Lignes avant filtrage : {total_before}")
        print(f"   ✅ Lignes après filtrage : {total_after}")
        print(f"   ❌ Dimanches retirés : {removed}")
        
        # Enlever les lignes avec des valeurs manquantes
        dataset_clean = dataset.dropna()
        
        output_path = '/app/data/ml_dataset_simplified.csv'
        dataset_clean.to_csv(output_path, index=False)
        
        print(f"   💾 Dataset sauvegardé : {output_path}")
        print(f"   📊 {len(dataset_clean)} lignes (après nettoyage)")
        print(f"   📋 {len(dataset_clean.columns)} colonnes")
        
        print("\n" + "="*70)
        print("📊 FEATURES DU DATASET")
        print("="*70)
        print("\n🌱 Features de base :")
        print("  • date, day_number, plants_nbrs, kg_produced, year, variety")
        print("  • harvest_fraction (1/3 ou 1/2 selon le jour)")
        print("  • kg_biological (capacité biologique = target principal)")
        
        print("\n🌤️  Features météo instantanées :")
        print("  • temperature_mean, temperature_min, temperature_max")
        print("  • humidity_mean, humidity_min, humidity_max")
        print("  • precipitation, sunshine_duration, solar_radiation")
        
        print("\n📈 Features moyennes glissantes (7 jours) :")
        print("  • temp_mean_7d, humidity_mean_7d")
        print("  • precipitation_7d_sum, sunshine_7d_sum, solar_radiation_7d_mean")
        print("  • kg_produced_7d_mean, kg_produced_7d_sum")
        print("  • kg_produced_prev_day")
        
        print("\n🌱 Features capacité biologique :")
        print("  • kg_biological_7d_mean (moyenne 7j de capacité)")
        print("  • kg_biological_14d_mean (moyenne 14j de capacité)")
        print("  • kg_biological_prev_day (capacité jour précédent)")
        
        print("\n🕐 Features temporelles :")
        print("  • month, day_of_week, week_of_year, day_of_year")
        print("  • days_since_season_start, temp_delta")
        
        print("\n📊 Features calculées :")
        print("  • kg_per_plant (rendement par plant)")
        
        print("="*70 + "\n")
        
        # Statistiques par variété
        print("📊 STATISTIQUES PAR VARIÉTÉ")
        print("="*70)
        for variety in sorted(dataset_clean['variety'].unique()):
            variety_data = dataset_clean[dataset_clean['variety'] == variety]
            print(f"\n{variety}:")
            print(f"  • Lignes : {len(variety_data)}")
            print(f"  • Années : {sorted(variety_data['year'].unique())}")
            print(f"  • Production moyenne : {variety_data['kg_produced'].mean():.2f} kg/jour")
            print(f"  • Production totale : {variety_data['kg_produced'].sum():.2f} kg")
            print(f"  • Rendement moyen : {variety_data['kg_per_plant'].mean():.4f} kg/plant/jour")
        
        print("="*70 + "\n")
        
        return dataset_clean
        
    finally:
        db.close()

if __name__ == "__main__":
    create_ml_dataset()