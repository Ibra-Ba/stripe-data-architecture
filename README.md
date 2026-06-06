# Stripe Data Architecture

**Jedha Bootcamp — Lead Data Science · Bloc 2**  
Conception et déploiement d'une architecture de données pour l'IA

---

## Contexte

Ce projet implémente une architecture de données complète inspirée de Stripe, couvrant l'ingestion transactionnelle, le streaming temps réel, le stockage analytique et la détection de fraude par machine learning.

**Problématique** : comment concevoir une architecture unifiée OLTP + OLAP + NoSQL capable de traiter des millions de transactions, détecter la fraude en temps réel et fournir des insights analytiques — le tout en free-tier ?

---

## Architecture

```
Sources synthétiques (Faker)
         ↓
NeonDB (OLTP) ──► CDC poller Python ──► Kafka (Confluent Cloud) ──► MongoDB Atlas (NoSQL)
      │
      ↓
GitHub Actions ──► AWS S3 (Parquet) ──► DuckDB (OLAP star schema)
      │
      ↓
scikit-learn + MLflow ──► Streamlit Dashboard (HuggingFace Spaces)
```

### Stack technique

| Couche | Outil | Free-tier |
|--------|-------|-----------|
| OLTP | NeonDB (PostgreSQL 16) | Permanent |
| CDC streaming | CDC poller Python + Kafka Confluent | 30 jours |
| NoSQL | MongoDB Atlas M0 | Permanent |
| Data Lake | AWS S3 Parquet | 12 mois |
| OLAP | DuckDB — star schema natif | Open source |
| Orchestration | GitHub Actions — cron + triggers | Permanent |
| ML tracking | scikit-learn + MLflow (NeonDB + S3) | Permanent |
| Serving | Streamlit — HuggingFace Spaces | Permanent |

### Justifications académiques

> **Debezium → CDC poller Python** : NeonDB free tier ne supporte pas le logical replication WAL nécessaire à Debezium. Le CDC poller simule ce comportement avec un polling toutes les 10 secondes.

> **Databricks/Spark → DuckDB** : DuckDB interroge directement les fichiers Parquet sur S3 sans cluster — approche analytique moderne et zéro infrastructure.

> **Airflow → GitHub Actions** : orchestration batch via cron natif, intégré au repo, sans infra supplémentaire. En production, Airflow orchestrerait des pipelines plus complexes.

---

## Structure du projet

```
stripe-data-architecture/
├── data_generator/
│   ├── config.py                    # Configuration partagée
│   ├── generate_customers.py        # 499 customers synthétiques
│   ├── generate_merchants.py        # 50 marchands synthétiques
│   └── generate_transactions.py     # 5000 transactions (fraud_score déterministe)
│
├── oltp/
│   ├── schema.sql                   # Schéma 3NF + index + RBAC
│   ├── seed.py                      # Orchestration du seeding
│   └── queries.sql                  # Requêtes transactionnelles clés
│
├── pipeline/
│   ├── cdc/
│   │   └── cdc_poller.py           # CDC polling NeonDB → Kafka (10s)
│   ├── kafka_consumer.py            # Consumer Kafka → MongoDB
│   ├── oltp_to_s3.py               # Export batch NeonDB → S3 (horaire)
│   └── oltp_to_s3_full.py          # Export complet NeonDB → S3
│
├── olap/
│   ├── star_schema.py              # DuckDB star schema depuis S3
│   └── test_duckdb_s3.py           # Test connexion DuckDB/S3
│
├── nosql/
│   └── (schémas MongoDB définis dans kafka_consumer.py)
│
├── ml/
│   ├── feature_engineering.py      # 14 features depuis DuckDB/S3
│   ├── train.py                    # RandomForest + MLflow tracking
│   └── predict.py                  # Inférence single + batch
│
├── serving/
│   ├── app.py                      # Dashboard Streamlit — page d'accueil
│   ├── Dockerfile                  # Docker pour HuggingFace Spaces
│   └── pages/
│       ├── 01_fraud_detection.py   # Détection fraude temps réel
│       ├── 02_revenue_analytics.py # Métriques OLAP
│       └── 03_fraud_by_country.py  # Analyse géographique
│
├── security/
│   ├── rbac_neondb.sql             # Rôles et permissions PostgreSQL
│   ├── pseudonymization.py         # Masquage PII (email → SHA-256)
│   └── audit_log_schema.sql        # Schéma audit_logs
│
├── docs/
│   ├── architecture_diagram_v2.svg # Diagramme d'architecture
│   ├── ERD_OLTP.png               # ERD généré depuis NeonDB
│   └── stripe_bloc2_presentation.pptx  # Présentation jury 14 slides
│
├── .github/workflows/
│   ├── oltp_to_s3.yml             # Export horaire NeonDB → S3
│   ├── s3_to_olap.yml             # Star schema DuckDB (post S3)
│   └── ml_retrain.yml             # Retraining hebdo (lundi 2h UTC)
│
├── .env.example                    # Template variables d'environnement
├── requirements.txt                # Dépendances Python
└── Makefile                        # Commandes raccourcis
```

---

## Prérequis

- Python 3.11
- Conda / Miniforge
- WSL2/Ubuntu (ou Linux/macOS)
- Comptes : NeonDB · AWS · Confluent Cloud · MongoDB Atlas · HuggingFace

---

## Installation

```bash
# Cloner le repo
git clone https://github.com/VoxUp/stripe-data-architecture.git
cd stripe-data-architecture
git checkout develop

# Créer l'environnement
conda create -n stripe-data python=3.11 -y
conda activate stripe-data
pip install setuptools==70.3.0
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Remplir les valeurs dans .env
```

### Variables d'environnement

```bash
# NeonDB (OLTP)
NEONDB_URL=postgresql://user:password@host/neondb?sslmode=require

# AWS S3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-west-1
S3_BUCKET=s3-bucket

# Confluent Cloud (Kafka)
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.eu-west-1.aws.confluent.cloud:9092
KAFKA_API_KEY=
KAFKA_API_SECRET=

# MongoDB Atlas
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/stripe_nosql

# MLflow
MLFLOW_TRACKING_URI=postgresql://user:password@host/mlflow
MLFLOW_ARTIFACT_ROOT=s3://mlflow-artifact-root/
```

---

## Quickstart

### 1. Initialiser la base OLTP

```bash
# Appliquer le schéma
psql $NEONDB_URL -f oltp/schema.sql

# Seeder les données (499 customers · 50 merchants · 5000 transactions)
cd data_generator && python generate_customers.py
python generate_merchants.py && python generate_transactions.py
cd .. && python oltp/seed.py
```

### 2. Lancer le pipeline streaming

```bash
# Terminal 1 — CDC poller (NeonDB → Kafka)
python pipeline/cdc/cdc_poller.py

# Terminal 2 — Consumer (Kafka → MongoDB)
python pipeline/kafka_consumer.py
```

### 3. Exporter vers S3 et construire le star schema

```bash
python pipeline/oltp_to_s3_full.py
python olap/star_schema.py
```

### 4. Entraîner le modèle ML

```bash
python ml/train.py
```

### 5. Lancer le dashboard localement

```bash
cd serving && streamlit run app.py
```

---

## GitHub Actions — workflows automatisés

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `oltp_to_s3.yml` | Cron horaire | Export NeonDB → S3 Parquet |
| `s3_to_olap.yml` | Après OLTP to S3 | Reconstruction star schema DuckDB |
| `ml_retrain.yml` | Lundi 2h UTC | Retraining fraud detection model |

Les secrets GitHub requis : `NEONDB_URL` · `AWS_ACCESS_KEY_ID` · `AWS_SECRET_ACCESS_KEY` · `AWS_REGION` · `S3_BUCKET` · `MLFLOW_TRACKING_URI` · `MLFLOW_ARTIFACT_ROOT`

---

## Modèle ML — résultats

| Métrique | Score |
|----------|-------|
| ROC-AUC | 0.9995 |
| PR-AUC | 0.9773 |
| F1-score | 0.8649 |
| Recall | 0.9412 |
| Precision | 0.8000 |
| CV ROC-AUC | 0.9968 ± 0.004 |

**Features principales** : `high_risk_country` · `amount_log` · `amount` · `status_failed` · `is_night`

**Dataset** : 5 003 transactions · 248 fraudes (5%) · train/test 80/20 stratifié · class weight balanced

---

## Dashboard

**URL** : [https://huggingface.co/spaces/VoxUp/stripe-demo](https://huggingface.co/spaces/VoxUp/stripe-demo)

3 pages :
- **Fraud Detection** — simulation transaction temps réel, verdict HIGH/MEDIUM/LOW
- **Revenue Analytics** — KPIs, revenue par devise, top 10 marchands
- **Fraud by Country** — taux de fraude par pays, carte choropleth

---

## Sécurité & conformité

| Mesure | Implémentation |
|--------|----------------|
| Encryption at rest | S3 SSE · NeonDB TLS |
| Encryption in transit | TLS (Kafka · MongoDB · NeonDB) |
| RBAC | `stripe_reader` · `stripe_writer` · `stripe_admin` |
| GDPR | Pseudonymisation email → SHA-256 |
| Audit | Table `audit_logs` (INSERT/UPDATE/DELETE) |
| PCI-DSS | Pas de stockage de données de carte |

---

## Livrables

| Livrable | Fichier |
|----------|---------|
| Diagramme d'architecture | `docs/architecture_diagram_v2.svg` |
| ERD OLTP | `docs/ERD_OLTP.png` |
| Présentation 14 slides | `docs/stripe_bloc2_presentation.pptx` |
| Code pipeline | `pipeline/` |
| Code ML | `ml/` |
| Dashboard live | [HF Spaces](https://huggingface.co/spaces/VoxUp/stripe-demo) |
| Repo GitHub | [VoxUp/stripe-data-architecture](https://github.com/VoxUp/stripe-data-architecture) |

---

## Auteur

**Ibrahim BAH**  
Jedha Bootcamp — Lead Data Science · Bloc 2  
2026