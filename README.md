# 🍫 Nassau Candy Distributor — Streamlit Dashboard

Interactive dashboard for analyzing Nassau Candy shipment performance, route efficiency, factories, shipping modes, regions, sales and delivery lead times.

## Files required

Keep these files in the **same GitHub repository folder**:

```text
nassau-candy-streamlit/
├── app.py
├── Nassau Candy Distributor_original.csv
├── Factory Mapping.csv
├── requirements.txt
└── README.md
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push all five files to GitHub.
2. Open Streamlit Community Cloud.
3. Select **Create app**.
4. Select your GitHub repository.
5. Select the branch, normally `main`.
6. Set the main file to:
   `app.py`
7. Deploy.

## Important

The app uses relative paths based on the location of `app.py`, so it is suitable for GitHub/Streamlit deployment.

`Factory Mapping.csv` provides factory coordinates. The source data does not contain a direct product/order-to-factory key, so the dashboard assigns factories deterministically from `Order ID`. This keeps the assignment consistent between runs.

## GitHub

Do not upload Colab-specific commands such as:

```python
!pip install ...
!streamlit run ...
!pkill ...
```

The deployed Streamlit app only needs `app.py`, the two CSV files and `requirements.txt`.
