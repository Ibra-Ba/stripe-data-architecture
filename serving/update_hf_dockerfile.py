from huggingface_hub import HfApi

api = HfApi()

dockerfile = """FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \\
    streamlit \\
    plotly \\
    duckdb \\
    boto3 \\
    pymongo \\
    mlflow==2.9.2 \\
    scikit-learn \\
    pandas \\
    numpy \\
    python-dotenv \\
    setuptools==70.3.0 \\
    pyarrow

COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "app.py", \\
     "--server.port=7860", \\
     "--server.address=0.0.0.0"]
"""

api.upload_file(
    path_or_fileobj=dockerfile.encode(),
    path_in_repo="Dockerfile",
    repo_id="VoxUp/stripe-demo",
    repo_type="space",
)
print("Dockerfile updated.")