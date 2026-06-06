import os
import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, roc_auc_score,
    average_precision_score, confusion_matrix
)
from sklearn.utils.class_weight import compute_class_weight
from feature_engineering import load_features_from_duckdb, build_features

load_dotenv()

# ── MLflow setup ──────────────────────────
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
mlflow.set_experiment("stripe-fraud-detection")

def train():
    # ── Data ──────────────────────────────
    df_raw      = load_features_from_duckdb()
    df          = build_features(df_raw)

    feature_cols = [c for c in df.columns if c != "is_fraud"]
    X = df[feature_cols]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"Train: {len(X_train)} samples | Test: {len(X_test)} samples")
    print(f"Fraud rate — train: {y_train.mean()*100:.1f}% | test: {y_test.mean()*100:.1f}%")

    # ── Class weights (imbalanced dataset) ───
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    class_weight = dict(zip(classes, weights))

    # ── Hyperparams ───────────────────────
    params = {
        "n_estimators":      200,
        "max_depth":         10,
        "min_samples_split": 5,
        "min_samples_leaf":  2,
        "class_weight":      class_weight,
        "random_state":      42,
        "n_jobs":            -1,
    }

    # ── Training + MLflow ─────────────────
    with mlflow.start_run(run_name="stripe_RandomForest_fraud_v1"):

        model = RandomForestClassifier(**params)
        model.fit(X_train, y_train)

        # ── Metrics ───────────────────────
        y_pred      = model.predict(X_test)
        y_proba     = model.predict_proba(X_test)[:, 1]

        roc_auc     = roc_auc_score(y_test, y_proba)
        pr_auc      = average_precision_score(y_test, y_proba)
        report      = classification_report(y_test, y_pred, output_dict=True)
        cm          = confusion_matrix(y_test, y_pred)

        precision   = report["1"]["precision"]
        recall      = report["1"]["recall"]
        f1          = report["1"]["f1-score"]

        # ── Cross validation ──────────────
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")

        print(f"\n── Results ─────────────────────────")
        print(f"ROC-AUC     : {roc_auc:.4f}")
        print(f"PR-AUC      : {pr_auc:.4f}")
        print(f"Precision   : {precision:.4f}")
        print(f"Recall      : {recall:.4f}")
        print(f"F1-score    : {f1:.4f}")
        print(f"CV ROC-AUC  : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
        print(f"Confusion matrix:\n{cm}")

        # ── MLflow log ────────────────────
        mlflow.log_params({
            "n_estimators":      params["n_estimators"],
            "max_depth":         params["max_depth"],
            "min_samples_split": params["min_samples_split"],
            "min_samples_leaf":  params["min_samples_leaf"],
            "test_size":         0.2,
            "random_state":      42,
        })

        mlflow.log_metrics({
            "roc_auc":       roc_auc,
            "pr_auc":        pr_auc,
            "precision":     precision,
            "recall":        recall,
            "f1_score":      f1,
            "cv_roc_auc_mean": cv_scores.mean(),
            "cv_roc_auc_std":  cv_scores.std(),
        })

        # ── Feature importance ────────────
        fi = pd.Series(
            model.feature_importances_,
            index=feature_cols
        ).sort_values(ascending=False)
        print(f"\n── Feature importance ──────────────")
        print(fi.to_string())

        for feat, imp in fi.items():
            mlflow.log_metric(f"fi_{feat}", imp)

        # ── Log model ─────────────────────
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name="stripe-fraud-detector",
            input_example=X_test.iloc[:5],
        )

        run_id = mlflow.active_run().info.run_id
        print(f"\nMLflow run_id : {run_id}")
        print(f"Model registered as : stripe-fraud-detector")

    return model, feature_cols

if __name__ == "__main__":
    train()
