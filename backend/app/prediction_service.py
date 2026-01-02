import joblib
import pandas as pd
import requests
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from .models import Prediction, Variety, PlantConfiguration, HarvestRecord, WeatherData
from .database import SessionLocal

def get_weather_forecast(latitude: float = 43.1397, longitude: float = 6.1556, days: int = 7):
    """
    Récupère les prévisions météo depuis Open-Meteo
    """
    url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "sunshine_duration",
            "shortwave_radiation_sum"
        ],
        "forecast_days": days,
        "timezone": "Europe/Paris"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Convertir en DataFrame
    df = pd.DataFrame({
        'date': pd.to_datetime(data['daily']['time']),
        'temperature_max': data['daily']['temperature_2m_max'],
        'temperature_min': data['daily']['temperature_2m_min'],
        'temperature_mean': data['daily']['temperature_2m_mean'],
        'humidity_mean': data['daily']['relative_humidity_2m_mean'],
        'precipitation': data['daily']['precipitation_sum'],
        'sunshine_duration': [h / 3600 if h else 0 for h in data['daily']['sunshine_duration']],
        'solar_radiation': data['daily']['shortwave_radiation_sum']
    })
    
    return df


def get_current_plant_config(db: Session, variety_id: int, target_date: date):
    """
    Récupère la configuration de plants active pour une variété à une date donnée
    """
    config = db.query(PlantConfiguration).filter(
        PlantConfiguration.variety_id == variety_id,
        PlantConfiguration.start_date <= target_date,
        (PlantConfiguration.end_date.is_(None)) | (PlantConfiguration.end_date >= target_date)
    ).first()
    
    return config.plants_nbrs if config else 0


def calculate_features(
    db: Session,
    variety_id: int,
    variety_name: str,
    plants_nbrs: int,
    target_date: date,
    weather_forecast: dict,
    model_data: dict
):
    """
    Calcule les 27 features nécessaires pour la prédiction
    """
    # Récupérer historique des 14 derniers jours
    start_hist = target_date - timedelta(days=14)
    end_hist = target_date - timedelta(days=1)
    
    recent_harvests = db.query(HarvestRecord).filter(
        HarvestRecord.variety_id == variety_id,
        HarvestRecord.date >= start_hist,
        HarvestRecord.date <= end_hist
    ).order_by(HarvestRecord.date).all()
    
    if not recent_harvests:
        print(f"   ⚠️  Pas d'historique pour {variety_name}, skip")
        return None
    
    # Convertir en DataFrame
    hist_df = pd.DataFrame([{
        'date': h.date,
        'kg_produced': h.kg_produced,
        'day_of_week': h.date.weekday()
    } for h in recent_harvests])
    
    # Calculer kg_biological depuis historique
    harvest_fraction_map = {0: 1/3, 1: 1/3, 2: 1/3, 3: 1/2, 4: 1/2, 5: 1/2, 6: 0}
    hist_df['harvest_fraction'] = hist_df['day_of_week'].map(harvest_fraction_map)
    hist_df['kg_biological'] = hist_df['kg_produced'] / hist_df['harvest_fraction'].replace(0, 1)
    
    # Récupérer météo historique
    weather_hist = db.query(WeatherData).filter(
        WeatherData.date >= start_hist,
        WeatherData.date <= end_hist
    ).order_by(WeatherData.date).all()
    
    weather_df = pd.DataFrame([{
        'date': w.date,
        'temperature_mean': w.temperature_mean,
        'humidity_mean': w.humidity_mean,
        'precipitation': w.precipitation,
        'sunshine_duration': w.sunshine_duration,
        'solar_radiation': w.solar_radiation
    } for w in weather_hist])
    
    # Calculer moyennes 7j et 14j
    kg_biological_7d = hist_df.tail(7)['kg_biological'].mean()
    kg_biological_14d = hist_df['kg_biological'].mean()
    kg_biological_prev = hist_df.iloc[-1]['kg_biological'] if len(hist_df) > 0 else 0
    
    temp_mean_7d = weather_df.tail(7)['temperature_mean'].mean()
    humidity_mean_7d = weather_df.tail(7)['humidity_mean'].mean()
    precipitation_7d_sum = weather_df.tail(7)['precipitation'].sum()
    sunshine_7d_sum = weather_df.tail(7)['sunshine_duration'].sum()
    solar_radiation_7d_mean = weather_df.tail(7)['solar_radiation'].mean()
    
    # Features temporelles
    month = target_date.month
    week_of_year = target_date.isocalendar()[1]
    day_of_year = target_date.timetuple().tm_yday
    day_of_week = target_date.weekday()
    
    # Days since season start (approximation : depuis le 1er janvier de l'année)
    season_start = date(target_date.year, 1, 1)
    days_since_season_start = (target_date - season_start).days
    
    # Température delta
    temp_delta = weather_forecast['temperature_mean'] - temp_mean_7d
    
    # Rendement
    kg_per_plant = kg_biological_prev / plants_nbrs if plants_nbrs > 0 else 0
    
    # Encoder variety
    variety_mapping = model_data.get('variety_mapping', {})
    variety_encoded = [k for k, v in variety_mapping.items() if v == variety_name]
    variety_encoded = variety_encoded[0] if variety_encoded else 0
    
    # Créer le vecteur de features
    features = {
        'variety_encoded': variety_encoded,
        'plants_nbrs': plants_nbrs,
        'month': month,
        'week_of_year': week_of_year,
        'day_of_year': day_of_year,
        'day_of_week': day_of_week,
        'days_since_season_start': days_since_season_start,
        'temperature_mean': weather_forecast['temperature_mean'],
        'humidity_mean': weather_forecast['humidity_mean'],
        'precipitation': weather_forecast['precipitation'],
        'sunshine_duration': weather_forecast['sunshine_duration'],
        'solar_radiation': weather_forecast['solar_radiation'],
        'temp_mean_7d': temp_mean_7d,
        'humidity_mean_7d': humidity_mean_7d,
        'precipitation_7d_sum': precipitation_7d_sum,
        'sunshine_7d_sum': sunshine_7d_sum,
        'solar_radiation_7d_mean': solar_radiation_7d_mean,
        'temp_delta': temp_delta,
        'kg_biological_prev_day': kg_biological_prev,
        'kg_biological_7d_mean': kg_biological_7d,
        'kg_biological_14d_mean': kg_biological_14d,
        'kg_per_plant': kg_per_plant
    }
    
    return features


def generate_predictions(days: int = 7):
    """
    Génère les prédictions pour les N prochains jours
    """
    print("\n" + "="*70)
    print(f"🔮 GÉNÉRATION DES PRÉDICTIONS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    db = SessionLocal()
    
    try:
        # Charger le modèle
        print("📦 Chargement du modèle...")
        model_data = joblib.load('/app/data/strawberry_biological_model.pkl')
        model = model_data['model']
        feature_columns = model_data['feature_columns']
        harvest_fraction_map = model_data['harvest_fraction_map']
        
        print("✅ Modèle chargé\n")
        
        # Récupérer prévisions météo
        print(f"🌤️  Récupération prévisions météo ({days} jours)...")
        weather_forecasts = get_weather_forecast(days=days)
        print(f"✅ {len(weather_forecasts)} jours de prévisions\n")
        
        # Récupérer toutes les variétés
        varieties = db.query(Variety).all()
        print(f"🌱 {len(varieties)} variétés trouvées\n")
        
        today = datetime.now().date()
        total_predictions = 0
        
        # Pour chaque variété
        for variety in varieties:
            print(f"📊 {variety.name}:")
            
            # Pour chaque jour
            for day_offset in range(1, days + 1):
                target_date = today + timedelta(days=day_offset)
                
                # Récupérer config plants
                plants_nbrs = get_current_plant_config(db, variety.id, target_date)
                
                if plants_nbrs == 0:
                    print(f"   ⚠️  Pas de config plants pour {target_date}, skip")
                    continue
                
                # Récupérer prévision météo du jour
                weather_row = weather_forecasts.iloc[day_offset - 1]
                weather_dict = {
                    'temperature_mean': weather_row['temperature_mean'],
                    'humidity_mean': weather_row['humidity_mean'],
                    'precipitation': weather_row['precipitation'],
                    'sunshine_duration': weather_row['sunshine_duration'],
                    'solar_radiation': weather_row['solar_radiation']
                }
                
                # Calculer features
                features_dict = calculate_features(
                    db, variety.id, variety.name, plants_nbrs,
                    target_date, weather_dict, model_data
                )
                
                if not features_dict:
                    continue
                
                # Créer DataFrame dans l'ordre des features
                features_df = pd.DataFrame([features_dict])
                features_df = features_df[feature_columns]
                
                # Prédire
                kg_biological_pred = model.predict(features_df)[0]
                
                # Convertir en production observée
                harvest_fraction = harvest_fraction_map.get(target_date.weekday(), 0)
                kg_produced_pred = kg_biological_pred * harvest_fraction
                
                # Stocker en DB
                prediction = Prediction(
                    prediction_date=datetime.now(),
                    target_date=target_date,
                    variety_id=variety.id,
                    plants_nbrs=plants_nbrs,
                    kg_biological_predicted=round(kg_biological_pred, 2),
                    kg_produced_predicted=round(kg_produced_pred, 2),
                    harvest_fraction=harvest_fraction
                )
                db.add(prediction)
                total_predictions += 1
                
                print(f"   ✅ {target_date} : {kg_biological_pred:.1f} kg bio → {kg_produced_pred:.1f} kg prod")
            
            print()
        
        db.commit()
        
        print("="*70)
        print(f"✅ {total_predictions} prédictions générées et stockées")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    generate_predictions(days=7)