# OpsMind AI — 2-Minute Developer Demo Script

Welcome to **OpsMind AI**! This guide takes you through the core operational intelligence loop in under 2 minutes. You'll upload sales history, retrain our specialized local ML models, and see how the system generates revenue forecasts, customer sentiment classification, and personalized dining briefings.

---

## 🏁 Step 0: Setup and Authentication

First, ensure your backend server is running (`uvicorn app.main:app --reload` on port `8000`).

To interact with secure endpoints, you need a JWT token. Register a restaurant and log in to retrieve your token:

### 1. Register a Restaurant (Tenant)
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"email": "owner@tasteofindia.com", "password": "securepassword123", "restaurant_name": "Taste of India", "role": "OWNER"}'
```

### 2. Login to Get JWT Access Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=owner@tasteofindia.com&password=securepassword123"
```
*Save the `access_token` from the JSON response. In the commands below, replace `YOUR_JWT_TOKEN` with this token.*

---

## 📂 Step 1: Upload Sales History CSV
> *"Here's how a restaurant imports their sales history."*

OpsMind AI features a bulk CSV importer that validates sales transaction records, automatically maps them to menu items and customers, and isolates the data to your restaurant's tenant ID.

```bash
curl -X POST "http://localhost:8000/api/v1/data/upload-sales" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@scripts/generate_sales_dataset.py" # You can generate or upload a standard sales CSV file here
```
*(Note: A script to generate a sample sales dataset is available at `scripts/generate_sales_dataset.py` if you want to generate a custom CSV first. Or use any CSV with headers: `date, item_name, quantity, unit_price, total_amount`)*

---

## 🏋️ Step 2: Trigger Model Retraining
> *"The system trains a custom model on their data."*

Instead of relying on slow, expensive cloud LLMs for forecasting, OpsMind AI retrains local machine learning models (**XGBoost** for time-series forecasting and **K-Means** for RFM customer segmentation) directly on the newly uploaded data.

```bash
curl -X POST "http://localhost:8000/api/v1/ml/retrain?model_type=all" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json"
```
**What happens under the hood:**
- Features are engineered locally (revenue lags of 1, 7, and 14 days, rolling averages, weather context).
- Models are trained, serialized as incremented versions, and saved under `models/{tenant_id}/`.
- Metadata manifest `models/{tenant_id}/manifest.json` is updated atomically.
- An 8-week rolling backtest is executed to log forecast accuracy metrics.

---

## 📈 Step 3: View Revenue Forecast
> *"3-day revenue predictions powered by XGBoost."*

Query the 3-day predictive forecast. This merges the local XGBoost time-series outputs with OpenWeatherMap context and calculates mathematical confidence scores (variance analysis + R-squared fit).

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/forecast" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json"
```
**Key Highlights:**
- Predicts next 3 days of revenue (Day 1, Day 2, Day 3).
- Returns a combined confidence percentage and statistical trust factor.
- Gives a business impact description (e.g. telling the owner to expect higher weekend sales and adjust staffing).

---

## ⭐ Step 4: View Reputation & Sentiment
> *"AI reviews customer feedback locally, instantly."*

Customer reviews are categorized using a local **TF-IDF + Logistic Regression** pipeline. This provides sub-millisecond sentiment analysis. Gemini is reserved strictly as a fallback for drafting creative response replies to negative reviews.

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/reputation" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json"
```
**Key Highlights:**
- Fast, local sentiment classification (Positive / Neutral / Negative).
- Review reply drafts generated only for poor reviews (saving API credits).

---

## 👤 Step 5: View Customer Personas
> *"Customers automatically grouped into segments."*

Waiters can check a table-side briefing for checking-in customers. The **Persona Engine** uses local **K-Means Clustering** on RFM metrics (Recency, Frequency, Monetary) to assign dynamic labels.

```bash
curl -X GET "http://localhost:8000/api/v1/customers/1/briefing" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json"
```
**Key Highlights:**
- Classifies customers into segments (e.g. "VIP Regular", "Big Spender", "Occasional", "At-Risk").
- Generates a 3-bullet waitstaff cheat-sheet containing lifetime value (LTV), favorite dishes, and a suggested marketing action.

---

## 📈 Step 6: View Model Performance
> *"Real metrics proving the model works."*

Inspect the backtesting metrics to prove the system works. OpsMind AI continuously evaluates the XGBoost forecaster against a naive baseline.

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/model-performance" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "accept: application/json"
```
**Key Highlights:**
- **MAE Lift**: The percentage improvement of XGBoost forecasting vs. naive baseline (typically +34%).
- **Stability Ratio**: Standard deviation of weekly error metrics divided by the mean (12.92%).
- **Weekly Benchmark Logs**: Real historical week-by-week accuracy data.
