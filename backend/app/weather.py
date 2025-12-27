import requests
import pandas as pd
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import WeatherData

def fetch_weather_data(latitude:float, longitude:float, start_date:str, end_date: str):
    """
    Récupère les données météo depuis Open-Meteo
    
    Args:
        latitude: Latitude du lieu (ex: 43.1397 pour Hyeres)
        longitude: Longitude du lieu (ex: 6.1556 pour Hyeres)
        start_date: Date de début (format: YYYY-MM-DD)
        end_date: Date de fin (format: YYYY-MM-DD)
    """
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "sunshine_duration",
            "shortwave_radiation_sum"
        ],
        "timezone": "Europe/Paris"
    }
    
    print(f"📡 Récupération météo de {start_date} à {end_date}...")
    
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
        'sunshine_duration': [h / 3600 if h else 0 for h in data['daily']['sunshine_duration']],  # secondes → heures
        'solar_radiation': data['daily']['shortwave_radiation_sum']
    })
    
    print(f"✅ {len(df)} jours récupérés")
    
    return df

def import_weather_data(latitude: float = 43.1397, longitude: float = 6.1556):
    """
    Importe les données météo historiques dans la base de données
    Coordonnées par défaut: Hyeres, France
    """
    
    # Créer la table
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🌤️  IMPORT DES DONNÉES MÉTÉO (Culture en serre)")
        print("="*60 + "\n")
        
        periods = [
            ("2022-01-01", "2022-12-31"),
            ("2023-01-01", "2023-12-31"),
            ("2024-01-01", "2024-12-31"),
            ("2025-01-01", "2025-11-29")
        ]
        
        total_imported = 0
        
        for start_date, end_date in periods:
            df = fetch_weather_data(latitude, longitude, start_date, end_date)
            
            if df is None:
                continue
            
            for _, row in df.iterrows():
                existing = db.query(WeatherData).filter(
                    WeatherData.date == row['date'].date()
                ).first()
                
                if existing:
                    continue
                
                weather = WeatherData(
                    date=row['date'].date(),
                    temperature_max=row['temperature_max'],
                    temperature_min=row['temperature_min'],
                    temperature_mean=row['temperature_mean'],
                    humidity_mean=row['humidity_mean'],
                    precipitation=row['precipitation'],
                    sunshine_duration=row['sunshine_duration'],
                    solar_radiation=row['solar_radiation']
                )
                db.add(weather)
                total_imported += 1
            
            db.commit()
            print(f"✅ Période {start_date} à {end_date} importée")
        
        total_weather = db.query(WeatherData).count()
        
        print("\n" + "="*60)
        print(f"📊 STATISTIQUES")
        print("="*60)
        print(f"Total enregistrements météo : {total_weather}")
        print(f"Nouveaux enregistrements : {total_imported}")
        print("="*60 + "\n")
        
    finally:
        db.close()

if __name__ == "__main__":
    import_weather_data()