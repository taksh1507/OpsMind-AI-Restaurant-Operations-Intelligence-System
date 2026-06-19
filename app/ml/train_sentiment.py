"""Sentiment Classifier Training Pipeline.

Loads weak-labeled training data, maps labels to binary targets,
trains a Logistic Regression model using TF-IDF features, evaluates holdout
metrics, and serializes the trained pipeline to disk.
"""

import os
import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def train_sentiment_model(csv_path: str = "data/sentiment_train.csv", model_dir: str = "models"):
    """Load, split, train, score, and serialize the sentiment classifier pipeline."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training dataset CSV not found at: {csv_path}")
        
    print(f"Loading sentiment dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Use binary classification: Map positive -> 1, negative -> 0. Drop neutral.
    print("Preprocessing labels...")
    df_binary = df[df["sentiment_label"] != "neutral"].copy()
    
    df_binary["label"] = df_binary["sentiment_label"].map({"positive": 1, "negative": 0})
    
    # Extract features and target
    X = df_binary["review_text"]
    y = df_binary["label"]
    
    print(f"Dataset Size: {len(X)} samples (positive: {sum(y == 1)}, negative: {sum(y == 0)})")
    
    # Train/Test stratified split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Build sklearn Pipeline
    print("Constructing Pipeline (TfidfVectorizer -> LogisticRegression)...")
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42))
    ])
    
    # Fit the pipeline
    print("Training model...")
    pipeline.fit(X_train, y_train)
    
    # Predict and evaluate holdout
    y_pred = pipeline.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    
    print("\n" + "=" * 55)
    print("             SENTIMENT CLASSIFIER EVALUATION")
    print("=" * 55)
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f} (Target >= 0.75)")
    print("=" * 55 + "\n")
    
    # Save the pipeline
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "sentiment_v1.pkl")
    joblib.dump(pipeline, model_path)
    print(f"Successfully saved trained model pipeline to: {model_path}")
    
    return acc, prec, rec, f1


if __name__ == "__main__":
    train_sentiment_model()
