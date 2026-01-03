import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
import numpy as np

def train_biological_model():
    """
    Entraîne un modèle pour prédire la CAPACITÉ BIOLOGIQUE des fraises
    (et non la production observée)
    """
    
    print("\n" + "="*70)
    print("🌱 ENTRAÎNEMENT DU MODÈLE - CAPACITÉ BIOLOGIQUE")
    print("="*70 + "\n")
    
    # ============================================================
    # ÉTAPE 1 : Charger le dataset avec capacité biologique
    # ============================================================
    print("📊 Étape 1/7 : Chargement du dataset...")
    
    df = pd.read_csv('/app/data/ml_dataset_simplified.csv')
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"   ✅ {len(df)} lignes chargées")
    print(f"   📅 Période : {df['date'].min()} à {df['date'].max()}")
    print(f"   📋 {len(df.columns)} colonnes disponibles")
    print(f"   🌱 Variétés : {df['variety'].unique().tolist()}")
    
    # Vérifier que kg_biological existe
    if 'kg_biological' not in df.columns:
        raise ValueError("❌ Colonne 'kg_biological' manquante ! Exécutez d'abord create_ml_dataset_simplified.py")
    
    print(f"   ✅ Colonne 'kg_biological' détectée")
    
    # ============================================================
    # ÉTAPE 2 : Préparer les features
    # ============================================================
    print("\n🔧 Étape 2/7 : Préparation des features...")
    
    # Encoder la variété
    df['variety_encoded'] = pd.Categorical(df['variety']).codes
    
    # Sélectionner les features importantes
    feature_columns = [
        # ==========================================
        # FEATURES DE BASE
        # ==========================================
        'variety_encoded',      # Variété (Clery, Manon, etc.)
        'plants_nbrs',          # Nombre de plants
        
        # ==========================================
        # FEATURES TEMPORELLES (Saisonnalité)
        # ==========================================
        'month',                # Mois (1-12)
        'week_of_year',         # Semaine de l'année (1-52)
        'day_of_year',          # Jour de l'année (1-365)
        'day_of_week',          # Jour de la semaine (0-6)
        'days_since_season_start',  # ⭐ TRÈS IMPORTANT - Phase de maturation
        
        # ==========================================
        # MÉTÉO DU JOUR (Conditions actuelles)
        # ==========================================
        'temperature_mean',     # Température moyenne du jour
        'humidity_mean',        # Humidité moyenne du jour
        'precipitation',        # Précipitations du jour
        'sunshine_duration',    # Ensoleillement du jour
        'solar_radiation',      # Rayonnement solaire du jour
        
        # ==========================================
        # MÉTÉO SUR 7 JOURS (Tendances)
        # ==========================================
        'temp_mean_7d',         # Température moyenne 7 derniers jours
        'humidity_mean_7d',     # Humidité moyenne 7 derniers jours
        'precipitation_7d_sum', # Précipitations cumulées 7j
        'sunshine_7d_sum',      # Ensoleillement cumulé 7j
        'solar_radiation_7d_mean', # Rayonnement solaire moyen 7j
        
        # ==========================================
        # CHANGEMENTS MÉTÉO (Chocs/Variations)
        # ==========================================
        'temp_delta',           # Changement de température vs moyenne 7j
        
        # ==========================================
        # PRODUCTION PASSÉE (Tendances biologiques)
        # ==========================================
        'kg_biological_prev_day',   # ⭐ Capacité biologique jour précédent
        'kg_biological_7d_mean',    # ⭐ Capacité moyenne 7 derniers jours
        'kg_biological_14d_mean',   # ⭐ Capacité moyenne 14 derniers jours
        
        # ==========================================
        # RENDEMENT
        # ==========================================
        'kg_per_plant'          # Production par plant
    ]
    
    # Vérifier que toutes les colonnes existent
    missing_cols = [col for col in feature_columns if col not in df.columns]
    if missing_cols:
        print(f"   ⚠️  Colonnes manquantes : {missing_cols}")
        print(f"   📋 Colonnes disponibles : {df.columns.tolist()}")
        feature_columns = [col for col in feature_columns if col in df.columns]
    
    print(f"   ✅ {len(feature_columns)} features sélectionnées")
    
    # Features (X) et cible (y)
    X = df[feature_columns]
    y = df['kg_biological']  # ⭐ CIBLE = CAPACITÉ BIOLOGIQUE
    
    print(f"\n   🎯 TARGET : kg_biological")
    print(f"      Moyenne : {y.mean():.2f} kg")
    print(f"      Min     : {y.min():.2f} kg")
    print(f"      Max     : {y.max():.2f} kg")
    
    # ============================================================
    # ÉTAPE 3 : Séparer en train/test (temporel)
    # ============================================================
    print("\n✂️  Étape 3/7 : Séparation train/test...")
    
    # Option 1 : Split temporel (recommandé pour les séries temporelles)
    # Les 80% les plus anciennes pour train, les 20% les plus récentes pour test
    df_sorted = df.sort_values('date')
    split_idx = int(len(df_sorted) * 0.8)
    
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]
    
    print(f"   ✅ Train : {len(X_train)} lignes (jusqu'à {df_sorted.iloc[split_idx-1]['date'].date()})")
    print(f"   ✅ Test  : {len(X_test)} lignes (à partir de {df_sorted.iloc[split_idx]['date'].date()})")
    
    # Option 2 : Split aléatoire (décommenter si vous préférez)
    # X_train, X_test, y_train, y_test = train_test_split(
    #     X, y, test_size=0.2, random_state=42, shuffle=True
    # )
    
    # ============================================================
    # ÉTAPE 4 : Tester plusieurs modèles
    # ============================================================
    print("\n🌳 Étape 4/7 : Test de plusieurs algorithmes...")
    
    models = {
        'Random Forest': RandomForestRegressor(
            n_estimators=200,        # Nombre d'arbres
            max_depth=15,            # Profondeur maximale
            min_samples_split=5,     # Min échantillons pour split
            min_samples_leaf=2,      # Min échantillons par feuille
            random_state=42,
            n_jobs=-1                # Utiliser tous les CPU
        ),
        'Gradient Boosting': GradientBoostingRegressor(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            min_samples_split=5,
            random_state=42
        )
    }
    
    best_model = None
    best_score = float('inf')
    best_name = ''
    
    results = {}
    
    for name, model in models.items():
        print(f"\n   🔄 Test de {name}...")
        
        # Entraîner
        model.fit(X_train, y_train)
        
        # Prédire
        y_pred = model.predict(X_test)
        
        # Métriques
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        # Erreur relative (en %)
        mask_non_zero = y_test > 0
        if mask_non_zero.sum() > 0:
            mape = np.mean(np.abs((y_test[mask_non_zero] - y_pred[mask_non_zero]) / y_test[mask_non_zero])) * 100
        else:
            mape = 0
        
        # Cross-validation sur le train
        cv_scores = cross_val_score(model, X_train, y_train, 
                                     cv=5, 
                                     scoring='neg_mean_absolute_error',
                                     n_jobs=-1)
        cv_mae = -cv_scores.mean()
        
        results[name] = {
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'mape': mape,
            'cv_mae': cv_mae
        }
        
        print(f"      MAE  : {mae:.2f} kg")
        print(f"      RMSE : {rmse:.2f} kg")
        print(f"      R²   : {r2:.3f}")
        print(f"      MAPE : {mape:.2f}%")
        print(f"      CV MAE: {cv_mae:.2f} kg (validation croisée)")
        
        # Garder le meilleur
        if mae < best_score:
            best_score = mae
            best_model = model
            best_name = name
    
    print(f"\n   🏆 Meilleur modèle : {best_name} (MAE: {best_score:.2f} kg)")
    
    # ============================================================
    # ÉTAPE 5 : Analyser le meilleur modèle
    # ============================================================
    print(f"\n📈 Étape 5/7 : Analyse du modèle {best_name}...")
    
    y_pred_best = best_model.predict(X_test)
    
    # Importance des features
    if hasattr(best_model, 'feature_importances_'):
        feature_importance = pd.DataFrame({
            'feature': feature_columns,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n   🔍 Top 15 features les plus importantes :")
        for idx, row in feature_importance.head(15).iterrows():
            print(f"      {row['feature']:<35} {row['importance']:.4f}")
    
    # Analyse des erreurs
    errors = np.abs(y_test.values - y_pred_best)
    print(f"\n   📊 Analyse des erreurs :")
    print(f"      Erreur moyenne    : {errors.mean():.2f} kg")
    print(f"      Erreur médiane    : {np.median(errors):.2f} kg")
    print(f"      Erreur max        : {errors.max():.2f} kg")
    print(f"      90% des erreurs < : {np.percentile(errors, 90):.2f} kg")
    
    # ============================================================
    # ÉTAPE 6 : Convertir les prédictions biologiques en production réelle
    # ============================================================
    print(f"\n🔄 Étape 6/7 : Conversion capacité biologique → production réelle...")
    
    # Récupérer les données de test avec day_of_week
    test_data = df.iloc[split_idx:].copy()
    test_data['kg_biological_pred'] = y_pred_best
    
    # Mapper day_of_week → harvest_fraction
    harvest_fraction_map = {
        0: 1/3,  # Lundi
        1: 1/3,  # Mardi
        2: 1/3,  # Mercredi
        3: 1/2,  # Jeudi
        4: 1/2,  # Vendredi
        5: 1/2,  # Samedi
        6: 0     # Dimanche (ne devrait pas exister après filtrage)
    }
    
    test_data['harvest_fraction'] = test_data['day_of_week'].map(harvest_fraction_map)
    
    # Convertir capacité biologique → production observée
    test_data['kg_produced_pred'] = test_data['kg_biological_pred'] * test_data['harvest_fraction']
    
    # Comparer avec la production réelle observée
    mae_observed = mean_absolute_error(test_data['kg_produced'], test_data['kg_produced_pred'])
    r2_observed = r2_score(test_data['kg_produced'], test_data['kg_produced_pred'])
    
    print(f"   📊 Performance sur production OBSERVÉE (kg_produced) :")
    print(f"      MAE  : {mae_observed:.2f} kg")
    print(f"      R²   : {r2_observed:.3f}")
    
    # ============================================================
    # ÉTAPE 7 : Sauvegarder le modèle
    # ============================================================
    print(f"\n💾 Étape 7/7 : Sauvegarde du modèle...")
    
    model_data = {
        'model': best_model,
        'model_name': best_name,
        'feature_columns': feature_columns,
        'variety_mapping': dict(enumerate(df['variety'].unique())),
        'harvest_fraction_map': harvest_fraction_map,
        'metrics': results[best_name],
        'metrics_observed': {
            'mae': mae_observed,
            'r2': r2_observed
        },
        'trained_on': pd.Timestamp.now().isoformat(),
        'target': 'kg_biological',  # Important : indique ce que prédit le modèle
        'note': 'Ce modèle prédit kg_biological. Pour obtenir kg_produced, multiplier par harvest_fraction.'
    }
    
    joblib.dump(model_data, '/app/data/strawberry_biological_model.pkl')
    
    print(f"   ✅ Modèle sauvegardé : /app/data/strawberry_biological_model.pkl")
    
    # ============================================================
    # EXEMPLES DE PRÉDICTIONS
    # ============================================================
    print("\n" + "="*70)
    print("🔮 EXEMPLES DE PRÉDICTIONS")
    print("="*70)
    
    # Prendre les 10 premiers exemples du test
    sample = test_data.head(10)
    
    comparison = pd.DataFrame({
        'Date': sample['date'].dt.strftime('%Y-%m-%d'),
        'Jour': sample['day_of_week'].map({0:'Lun', 1:'Mar', 2:'Mer', 3:'Jeu', 4:'Ven', 5:'Sam', 6:'Dim'}),
        'Variété': sample['variety'],
        'Capacité bio réelle': sample['kg_biological'].round(1),
        'Capacité bio prédite': sample['kg_biological_pred'].round(1),
        'Erreur bio (kg)': (sample['kg_biological_pred'] - sample['kg_biological']).round(1),
        'Prod. observée': sample['kg_produced'].round(1),
        'Prod. prédite': sample['kg_produced_pred'].round(1)
    })
    
    print("\n" + comparison.to_string(index=False))
    
    # ============================================================
    # RÉSUMÉ FINAL
    # ============================================================
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DU MODÈLE")
    print("="*70)
    print(f"\n🎯 TARGET : Capacité biologique (kg_biological)")
    print(f"   → Ce que produiraient TOUS les plants si récoltés")
    print(f"\n📈 Performance sur capacité biologique :")
    print(f"   MAE  : {best_score:.2f} kg")
    print(f"   RMSE : {results[best_name]['rmse']:.2f} kg")
    print(f"   R²   : {results[best_name]['r2']:.3f}")
    print(f"   MAPE : {results[best_name]['mape']:.2f}%")
    print(f"\n📊 Performance sur production observée (après conversion) :")
    print(f"   MAE  : {mae_observed:.2f} kg")
    print(f"   R²   : {r2_observed:.3f}")
    print(f"\n💡 UTILISATION :")
    print(f"   1. Le modèle prédit kg_biological")
    print(f"   2. Pour obtenir la production à récolter :")
    print(f"      • Lundi/Mardi/Mercredi : kg_biological × 1/3")
    print(f"      • Jeudi/Vendredi : kg_biological × 1/2")
    print("="*70 + "\n")
    
    return best_model, feature_columns, results, test_data

if __name__ == "__main__":
    train_biological_model()