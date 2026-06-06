.PHONY: seed pipeline serve deploy test

seed:
	python data_generator/generate_transactions.py
	python data_generator/generate_customers.py
	python data_generator/generate_merchants.py
	python oltp/seed.py

pipeline:
	airflow dags trigger oltp_to_s3_dag
	airflow dags trigger s3_to_spark_dag

serve:
	streamlit run serving/app.py

deploy:
	cd serving && huggingface-hub upload . VoxUp/stripe-demo

test:
	python -m pytest tests/ -v