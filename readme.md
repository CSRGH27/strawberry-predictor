# 🍓 Strawberry Production Predictor

Système de prédiction de production de fraises basé sur le Machine Learning, intégrant données historiques et météorologiques.

---

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Architecture du projet](#-architecture-du-projet)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Performances du modèle](#-performances-du-modèle)
- [API Documentation](#-api-documentation)
- [Structure des données](#-structure-des-données)
- [Développement](#-développement)

---

## 🎯 Vue d'ensemble

### Objectif

Prédire la **capacité biologique** de production de fraises (ce que les plants peuvent produire si tous récoltés) plutôt que la production observée qui dépend des contraintes opérationnelles.

### Concept clé : Capacité biologique

```
Capacité biologique = Production que TOUS les plants produiraient s'ils étaient récoltés
Production observée = Capacité biologique × Fraction récoltée

Exemple :
- Capacité biologique : 300 kg
- Jeudi (récolte 1/2 des plants) : 300 × 0.5 = 150 kg observés
```

### Planning de récolte

| Jour     | Fraction récoltée | Exemple (300 kg capacité) |
| -------- | ----------------- | ------------------------- |
| Lundi    | 1/3               | 100 kg                    |
| Mardi    | 1/3               | 100 kg                    |
| Mercredi | 1/3               | 100 kg                    |
| Jeudi    | 1/2               | 150 kg                    |
| Vendredi | 1/2               | 150 kg                    |
| Samedi   | 1/2               | 150 kg                    |
| Dimanche | 0                 | Pas de récolte            |

---

## 🏗️ Architecture du projet

### Stack technique

```
┌─────────────────────────────────────┐
│         Frontend (À venir)          │
│      HTML/JS ou React/Vue.js        │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│         Backend - FastAPI           │
│    • API REST                       │
│    • Prédictions ML                 │
│    • Gestion données                │
└─────────────────┬───────────────────┘
                  │
┌─────────────────▼───────────────────┐
│       PostgreSQL Database           │
│    • Harvest Records                │
│    • Weather Data                   │
│    • Varieties                      │
└─────────────────────────────────────┘
```

### Services Docker

```yaml
services:
  postgres: → localhost:5433 # Base de données
  backend: → localhost:8003 # API FastAPI
  adminer: → localhost:8083 # Interface DB
```

---

## 🚀 Installation

### Prérequis

- Docker & Docker Compose
- Git

### Étapes d'installation

```bash
# 1. Cloner le repository
git clone <votre-repo>
cd strawberry-predictor

# 2. Créer le fichier .env
cat > .env << EOF
POSTGRES_USER=strawberry_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=strawberry_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
EOF

# 3. Placer vos données Excel
# Copier data.xlsx dans backend/data/

# 4. Démarrer les services
docker-compose up -d

# 5. Vérifier que tout fonctionne
docker-compose ps
```

---

## 📊 Utilisation

### 1️⃣ Import des données

#### Importer les données de récolte

```bash
docker-compose exec backend python -m app.import_data
```

**Ce que ça fait** :

- Importe les variétés (Clery, Ciflorette, Manon, Dream)
- Charge les données historiques depuis `data.xlsx`
- Champs importés : `date`, `day_number`, `plants_nbrs`, `kg_produced`, `year`

**Sortie attendue** :

```
🍓 IMPORT DES DONNÉES DE RÉCOLTE
✅ Variété 'Clery' ajoutée
✅ Variété 'Ciflorette' ajoutée
...
🎉 Import terminé : XXX enregistrements ajoutés
```

---

#### Importer les données météo

```bash
docker-compose exec backend python -m app.weather
```

**Ce que ça fait** :

- Récupère données météo depuis Open-Meteo API (2022-2025)
- Coordonnées : Hyères, France (43.1397°N, 6.1556°E)
- Variables : température, humidité, précipitations, ensoleillement, radiation solaire

**Sortie attendue** :

```
🌤️  IMPORT DES DONNÉES MÉTÉO
📡 Récupération météo de 2022-01-01 à 2022-12-31...
✅ 365 jours récupérés
...
Total enregistrements météo : XXXX
```

---

### 2️⃣ Création du dataset ML

```bash
docker-compose exec backend python -m app.ml_dataset
```

**Ce que ça fait** :

1. Fusionne données de récolte + météo
2. Calcule la **capacité biologique** :
   ```
   kg_biological = kg_produced / harvest_fraction
   ```
3. Crée features temporelles (month, week, day_of_year, days_since_season_start)
4. Calcule moyennes glissantes (7j, 14j) pour météo et production
5. **Filtre les dimanches** (pas de récolte suffisante pour entraînement)
6. Sauvegarde : `/app/data/ml_dataset_simplified.csv`

**Features créées** (27 au total) :

| Catégorie             | Features                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| **Base**              | variety_encoded, plants_nbrs                                                                   |
| **Temporelles**       | month, week_of_year, day_of_year, day_of_week, days_since_season_start                         |
| **Météo actuelle**    | temperature_mean, humidity_mean, precipitation, sunshine_duration, solar_radiation             |
| **Météo 7j**          | temp_mean_7d, humidity_mean_7d, precipitation_7d_sum, sunshine_7d_sum, solar_radiation_7d_mean |
| **Variations**        | temp_delta                                                                                     |
| **Production passée** | kg_biological_prev_day, kg_biological_7d_mean, kg_biological_14d_mean                          |
| **Rendement**         | kg_per_plant                                                                                   |

**Sortie attendue** :

```
🤖 CRÉATION DU DATASET ML
✅ XXX enregistrements de récolte récupérés
✅ XXX enregistrements météo récupérés
✅ Capacité biologique calculée
💾 Dataset sauvegardé : /app/data/ml_dataset_simplified.csv
```

---

### 3️⃣ Entraînement du modèle

```bash
docker-compose exec backend python -m app.ml_model
```

**Ce que ça fait** :

1. Charge le dataset ML
2. Prépare les features (encodage, sélection)
3. **Split temporel 80/20** (évite data leakage)
4. Teste 2 algorithmes : Random Forest vs Gradient Boosting
5. Sélectionne le meilleur modèle
6. Sauvegarde : `/app/data/strawberry_biological_model.pkl`

**Sortie attendue** :

```
🌱 ENTRAÎNEMENT DU MODÈLE - CAPACITÉ BIOLOGIQUE
✅ XXX lignes chargées
🏆 Meilleur modèle : Random Forest (MAE: 22.85 kg)

📊 RÉSUMÉ DU MODÈLE
🎯 TARGET : Capacité biologique (kg_biological)
📈 Performance sur capacité biologique :
   MAE  : 22.85 kg
   RMSE : 37.59 kg
   R²   : 0.960
   MAPE : 14.75%
📊 Performance sur production observée (après conversion) :
   MAE  : 9.15 kg
   R²   : 0.958
```

---

## 📈 Performances du modèle

### Métriques obtenues

| Métrique | Valeur   | Signification                                  |
| -------- | -------- | ---------------------------------------------- |
| **MAE**  | 22.85 kg | Erreur moyenne absolue sur capacité biologique |
| **RMSE** | 37.59 kg | Erreur quadratique (pénalise les outliers)     |
| **R²**   | 0.960    | 96% de la variance expliquée                   |
| **MAPE** | 14.75%   | Erreur relative moyenne de ~15%                |

### Interprétation détaillée

#### 1️⃣ **MAE = 22.85 kg** (Mean Absolute Error)

**Définition** : Moyenne des erreurs en valeur absolue

**Exemple concret** :

```
Jour 1 : Réel = 300 kg, Prédit = 320 kg → Erreur = 20 kg
Jour 2 : Réel = 250 kg, Prédit = 240 kg → Erreur = 10 kg
Jour 3 : Réel = 200 kg, Prédit = 230 kg → Erreur = 30 kg
→ MAE = (20 + 10 + 30) / 3 = 20 kg
```

**Pour vous** :

- En moyenne, le modèle se trompe de **±22.85 kg**
- Si capacité réelle = 300 kg → prédiction entre **277 et 323 kg**

---

#### 2️⃣ **RMSE = 37.59 kg** (Root Mean Squared Error)

**Définition** : Racine carrée de la moyenne des erreurs au carré

**Pourquoi > MAE ?** → Pénalise davantage les **grosses erreurs**

**Ratio RMSE/MAE** :

```
37.59 / 22.85 = 1.65

• Ratio = 1.0 → Erreurs homogènes
• Ratio = 1.5-2.0 → Quelques outliers (votre cas ✅)
• Ratio > 2.0 → Beaucoup d'outliers ❌
```

**Pour vous** :

- Quelques prédictions ont des erreurs plus importantes
- 95% du temps : erreur < 75 kg (2×RMSE)

---

#### 3️⃣ **R² = 0.960** (Coefficient de détermination)

**Définition** : Pourcentage de variance expliquée par le modèle

**Échelle** :

```
R² = 1.0   → Prédictions parfaites 🎯
R² = 0.9   → Excellent ✅ ← VOUS ÊTES ICI
R² = 0.7   → Bon
R² = 0.5   → Moyen
R² = 0.0   → Modèle inutile (prédire la moyenne)
```

**Pour vous** :

- Le modèle explique **96% des variations** de production
- Seulement **4% reste inexpliqué** (aléatoire, facteurs non mesurés)

---

#### 4️⃣ **MAPE = 14.75%** (Mean Absolute Percentage Error)

**Définition** : Erreur moyenne en pourcentage

**Exemples concrets** :

| Production réelle | Erreur ±14.75% | Plage prédite |
| ----------------- | -------------- | ------------- |
| 100 kg            | ±15 kg         | 85 - 115 kg   |
| 200 kg            | ±30 kg         | 170 - 230 kg  |
| 300 kg            | ±44 kg         | 256 - 344 kg  |
| 500 kg            | ±74 kg         | 426 - 574 kg  |

**Échelle** :

```
MAPE < 10%  → Excellent 🎯
MAPE 10-20% → Bon ✅ ← VOUS ÊTES ICI
MAPE 20-30% → Moyen
MAPE > 30%  → Faible
```

---

### Exemple pratique complet

**Scénario** : Jeudi, 5000 plants de Clery

```
1. Modèle prédit : kg_biological = 300 kg
2. Fraction jeudi = 1/2
3. Production à récolter = 300 × 0.5 = 150 kg
4. Erreur probable (MAE après conversion) = ±9 kg
5. Plage réaliste = 141 - 159 kg
```

**Précision relative** :

```
9 kg / 150 kg = 6% d'erreur sur la production observée
```

---

## 🔌 API Documentation

### Endpoints disponibles

#### Variétés

```bash
# Liste des variétés
GET http://localhost:8003/api/varieties

# Détail d'une variété
GET http://localhost:8003/api/varieties/{id}
```

#### Récoltes

```bash
# Liste des récoltes (avec filtres)
GET http://localhost:8003/api/harvests?variety_id=1&year=2024&limit=100

# Détail d'une récolte
GET http://localhost:8003/api/harvests/{id}
```

#### Statistiques

```bash
# Statistiques globales
GET http://localhost:8003/api/stats/summary?variety_id=1&year=2024

# Statistiques par variété
GET http://localhost:8003/api/stats/by-variety?year=2024
```

#### Documentation interactive

- **Swagger UI** : http://localhost:8003/docs
- **ReDoc** : http://localhost:8003/redoc

---

## 📁 Structure des données

### Modèles de base de données

#### Variety (Variétés)

```python
{
  "id": 1,
  "name": "Clery",
  "description": "Variété précoce..."
}
```

#### HarvestRecord (Enregistrements de récolte)

```python
{
  "id": 1,
  "date": "2024-03-15",
  "day_number": 45,
  "plants_nbrs": 5000,
  "kg_produced": 150.5,
  "year": 2024,
  "variety_id": 1
}
```

#### WeatherData (Données météo)

```python
{
  "id": 1,
  "date": "2024-03-15",
  "temperature_max": 24.5,
  "temperature_min": 12.3,
  "temperature_mean": 18.4,
  "humidity_mean": 65.2,
  "precipitation": 0.0,
  "sunshine_duration": 8.5,
  "solar_radiation": 18.2
}
```

---

## 🔧 Développement

### Accéder au container

```bash
# Shell dans le container backend
docker-compose exec backend bash

# Logs en temps réel
docker-compose logs -f backend
```

### Accéder à la base de données

#### Via Adminer (interface web)

- URL : http://localhost:8083
- Système : PostgreSQL
- Serveur : `postgres`
- User/Password/DB : selon votre `.env`

#### Via psql (ligne de commande)

```bash
docker-compose exec postgres psql -U strawberry_user -d strawberry_db
```

### Structure du projet

```
strawberry-predictor/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Point d'entrée FastAPI
│   │   ├── database.py          # Configuration DB
│   │   ├── models.py            # Modèles SQLAlchemy
│   │   ├── schemas.py           # Schémas Pydantic
│   │   ├── routes.py            # Routes API
│   │   ├── import_data.py       # Import Excel
│   │   ├── weather.py           # Import météo
│   │   ├── ml_dataset.py        # Création dataset ML
│   │   └── ml_model.py          # Entraînement modèle
│   ├── data/
│   │   ├── data.xlsx            # Données sources (à fournir)
│   │   ├── ml_dataset_simplified.csv  # Dataset ML (généré)
│   │   └── strawberry_biological_model.pkl  # Modèle entraîné (généré)
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env                         # Variables d'environnement
├── .gitignore
└── README.md
```

---

## 🎯 Prochaines étapes

### Phase 1 : API de prédiction (En cours)

- [ ] Route `/api/predict/single` - Prédiction pour une date donnée
- [ ] Route `/api/predict/weekly` - Prédictions hebdomadaires
- [ ] Route `/api/predict/all-varieties` - Toutes variétés d'un coup

### Phase 2 : Automatisation

- [ ] Script de collecte météo quotidienne
- [ ] Script de génération prédictions automatiques
- [ ] Table `Prediction` en DB
- [ ] Notifications (email/SMS)

### Phase 3 : Interface web

- [ ] Dashboard de visualisation
- [ ] Formulaire de prédiction à la demande
- [ ] Historique prédictions vs réalité
- [ ] Monitoring performances modèle

### Phase 4 : Amélioration continue

- [ ] Comparaison prédictions vs réalité
- [ ] Re-entraînement automatique
- [ ] Versioning des modèles
- [ ] Alertes intelligentes

---

## 🤝 Support

Pour toute question ou problème :

1. Vérifier les logs : `docker-compose logs backend`
2. Vérifier la base de données via Adminer
3. Consulter la documentation API : http://localhost:8003/docs

---

## 📄 Licence

[À définir]

---

## 🙏 Remerciements

- **Open-Meteo** pour les données météorologiques gratuites
- **FastAPI** pour le framework web
- **Scikit-learn** pour les outils ML

---

**Version** : 1.0.0  
**Dernière mise à jour** : Décembre 2024
