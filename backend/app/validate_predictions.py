#!/usr/bin/env python3
"""
Script de validation des prédictions
Compare les prédictions générées avec les vraies données de récolte
"""
from datetime import date, timedelta
from .database import SessionLocal
from .models import Prediction, HarvestRecord, Variety
from .prediction_service import generate_predictions
import pandas as pd
from sqlalchemy import func

def validate_predictions(test_date: date, days: int = 7, generate_first: bool = False):
    """
    Valide les prédictions en les comparant avec les vraies données
    
    Args:
        test_date: Date de référence pour le test
        days: Nombre de jours à prédire
        generate_first: Si True, génère d'abord les prédictions
    """
    
    print("\n" + "="*80)
    print("🔍 VALIDATION DES PRÉDICTIONS")
    print("="*80 + "\n")
    
    # 1. Générer les prédictions si demandé
    if generate_first:
        print(f"🔮 Génération des prédictions depuis {test_date}...\n")
        generate_predictions(days=days, test_date=test_date)
        print("\n" + "="*80 + "\n")
    
    # 2. Récupérer et comparer
    db = SessionLocal()
    
    try:
        results = []
        
        print(f"📊 Comparaison prédictions vs réalité ({test_date + timedelta(days=1)} → {test_date + timedelta(days=days)})\n")
        
        for day_offset in range(1, days + 1):
            target = test_date + timedelta(days=day_offset)
            
            # Skip dimanche
            if target.weekday() == 6:
                continue
            
            # Récupérer prédictions pour ce jour
            preds = db.query(Prediction).filter(
                Prediction.target_date == target
            ).all()
            
            if not preds:
                print(f"   ⚠️  {target} : Aucune prédiction trouvée")
                continue
            
            for pred in preds:
                # Récupérer la vraie récolte
                real = db.query(HarvestRecord).filter(
                    HarvestRecord.date == target,
                    HarvestRecord.variety_id == pred.variety_id
                ).first()
                
                if not real:
                    print(f"   ⚠️  {target} : Pas de données réelles pour {pred.variety.name}")
                    continue
                
                # Calculer erreurs
                error_kg = pred.kg_produced_predicted - real.kg_produced
                error_abs = abs(error_kg)
                error_pct = (error_abs / real.kg_produced * 100) if real.kg_produced > 0 else 0
                
                # Calculer capacité biologique réelle
                harvest_fraction = pred.harvest_fraction
                kg_biological_real = real.kg_produced / harvest_fraction if harvest_fraction > 0 else 0
                error_bio = pred.kg_biological_predicted - kg_biological_real
                error_bio_abs = abs(error_bio)
                
                results.append({
                    'date': target,
                    'jour': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][target.weekday()],
                    'variety': pred.variety.name,
                    'fraction': f"{int(harvest_fraction * 100)}%",
                    'bio_pred': round(pred.kg_biological_predicted, 1),
                    'bio_real': round(kg_biological_real, 1),
                    'error_bio': round(error_bio, 1),
                    'prod_pred': round(pred.kg_produced_predicted, 1),
                    'prod_real': round(real.kg_produced, 1),
                    'error_kg': round(error_kg, 1),
                    'error_abs': round(error_abs, 1),
                    'error_pct': round(error_pct, 1)
                })
        
        if not results:
            print("❌ Aucune donnée à comparer\n")
            return None
        
        # Créer DataFrame
        df = pd.DataFrame(results)
        
        # Afficher résultats détaillés
        print("="*80)
        print("📋 RÉSULTATS DÉTAILLÉS")
        print("="*80 + "\n")
        
        # Formater l'affichage
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', None)
        pd.set_option('display.max_columns', None)
        
        print(df[['date', 'jour', 'variety', 'fraction', 'prod_pred', 'prod_real', 'error_kg', 'error_pct']].to_string(index=False))
        
        # Statistiques globales
        print("\n" + "="*80)
        print("📈 STATISTIQUES GLOBALES")
        print("="*80)
        
        print(f"\n🎯 Performance sur PRODUCTION OBSERVÉE (kg_produced) :")
        print(f"   MAE   : {df['error_abs'].mean():.2f} kg")
        print(f"   RMSE  : {(df['error_kg']**2).mean()**0.5:.2f} kg")
        print(f"   MAPE  : {df['error_pct'].mean():.2f}%")
        print(f"   Max   : {df['error_abs'].max():.2f} kg")
        print(f"   Min   : {df['error_abs'].min():.2f} kg")
        print(f"   Médiane: {df['error_abs'].median():.2f} kg")
        
        print(f"\n🌱 Performance sur CAPACITÉ BIOLOGIQUE (kg_biological) :")
        bio_mae = df['error_bio'].abs().mean()
        bio_rmse = (df['error_bio']**2).mean()**0.5
        print(f"   MAE   : {bio_mae:.2f} kg")
        print(f"   RMSE  : {bio_rmse:.2f} kg")
        
        # Statistiques par variété
        print("\n" + "="*80)
        print("📊 STATISTIQUES PAR VARIÉTÉ")
        print("="*80 + "\n")
        
        for variety in df['variety'].unique():
            variety_df = df[df['variety'] == variety]
            print(f"{variety}:")
            print(f"   Prédictions : {len(variety_df)}")
            print(f"   MAE         : {variety_df['error_abs'].mean():.2f} kg")
            print(f"   MAPE        : {variety_df['error_pct'].mean():.2f}%")
            print(f"   Production moyenne prédite : {variety_df['prod_pred'].mean():.1f} kg")
            print(f"   Production moyenne réelle  : {variety_df['prod_real'].mean():.1f} kg")
            print()
        
        # Statistiques par jour de semaine
        print("="*80)
        print("📅 STATISTIQUES PAR JOUR DE SEMAINE")
        print("="*80 + "\n")
        
        for jour in ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']:
            jour_df = df[df['jour'] == jour]
            if len(jour_df) > 0:
                print(f"{jour} (fraction {jour_df.iloc[0]['fraction']}):")
                print(f"   MAE  : {jour_df['error_abs'].mean():.2f} kg")
                print(f"   MAPE : {jour_df['error_pct'].mean():.2f}%")
                print()
        
        # Analyse des sur/sous-estimations
        print("="*80)
        print("⚖️  ANALYSE DES BIAIS")
        print("="*80)
        
        over = df[df['error_kg'] > 0]
        under = df[df['error_kg'] < 0]
        
        print(f"\nSur-estimations  : {len(over)} cas ({len(over)/len(df)*100:.1f}%)")
        print(f"Sous-estimations : {len(under)} cas ({len(under)/len(df)*100:.1f}%)")
        print(f"Biais moyen      : {df['error_kg'].mean():.2f} kg")
        
        if df['error_kg'].mean() > 5:
            print("   ⚠️  Le modèle a tendance à SUR-ESTIMER la production")
        elif df['error_kg'].mean() < -5:
            print("   ⚠️  Le modèle a tendance à SOUS-ESTIMER la production")
        else:
            print("   ✅ Le modèle est bien calibré (peu de biais)")
        
        print("\n" + "="*80 + "\n")
        
        # Sauvegarder les résultats
        output_file = f"/app/data/validation_{test_date.strftime('%Y-%m-%d')}.csv"
        df.to_csv(output_file, index=False)
        print(f"💾 Résultats sauvegardés : {output_file}\n")
        
        return df
        
    finally:
        db.close()


def compare_multiple_periods():
    """
    Compare les prédictions sur plusieurs périodes
    """
    
    print("\n" + "="*80)
    print("🔬 VALIDATION SUR PLUSIEURS PÉRIODES")
    print("="*80 + "\n")
    
    test_dates = [
        date(2025, 4, 15),  # Début de saison
        date(2025, 6, 1),   # Milieu de saison
        date(2025, 9, 1),   # Fin de saison
    ]
    
    all_results = []
    
    for test_date in test_dates:
        print(f"\n{'='*80}")
        print(f"📅 Test période : {test_date}")
        print(f"{'='*80}\n")
        
        df = validate_predictions(test_date, days=7, generate_first=True)
        
        if df is not None:
            all_results.append({
                'periode': test_date.strftime('%Y-%m-%d'),
                'mae': df['error_abs'].mean(),
                'mape': df['error_pct'].mean(),
                'rmse': (df['error_kg']**2).mean()**0.5,
                'nb_predictions': len(df)
            })
    
    if all_results:
        summary = pd.DataFrame(all_results)
        
        print("\n" + "="*80)
        print("📊 RÉSUMÉ COMPARATIF")
        print("="*80 + "\n")
        print(summary.to_string(index=False))
        print()


if __name__ == "__main__":
    import sys
    
    # Configuration par défaut
    TEST_DATE = date(2025, 4, 15)
    DAYS = 7
    
    validate_predictions(test_date=TEST_DATE, days=DAYS, generate_first=False)