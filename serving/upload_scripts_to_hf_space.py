from huggingface_hub import HfApi

api = HfApi()

files = {
    "serving/app.py":                        "app.py",
    "serving/pages/01_fraud_detection.py":   "pages/01_fraud_detection.py",
    "serving/pages/02_revenue_analytics.py": "pages/02_revenue_analytics.py",
    "serving/pages/03_fraud_by_country.py":  "pages/03_fraud_by_country.py",
    "ml/feature_engineering.py":             "ml/feature_engineering.py",
    "ml/predict.py":                         "ml/predict.py",
}

for local, remote in files.items():
    api.upload_file(
        path_or_fileobj=local,
        path_in_repo=remote,
        repo_id="VoxUp/stripe-demo",
        repo_type="space",
    )
    print(f"Uploaded {local} → {remote}")

print("\nDone : https://huggingface.co/spaces/VoxUp/stripe-demo")
