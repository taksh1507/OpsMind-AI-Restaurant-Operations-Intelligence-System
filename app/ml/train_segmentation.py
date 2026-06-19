"""Customer Segmentation Trainer.

Loads behavioral features, preprocesses them (Scaling + One-Hot Encoding),
runs K-Means with Silhouette Score optimization across a range of k (3 to 6),
dynamically profiles clusters to map to distinct customer personas,
and serializes the pipeline to models/{tenant_id}/segments_v1.pkl.
"""

import os
from typing import Dict, Any, List
import joblib
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from app.ml.segmentation_features import build_segmentation_features


def train_customer_segmentation(
    df_features: pd.DataFrame,
    tenant_id: int,
    model_dir: str = "models",
    version: int = None,
    reason: str = "manual"
) -> Dict[str, Any]:
    """Train customer segmentation model using K-Means and save it.
    
    Args:
        df_features: DataFrame containing customer behavioral features
        tenant_id: The tenant identifier
        model_dir: Base directory to save models
        
    Returns:
        Dict containing training metadata
    """
    n_samples = len(df_features)
    if n_samples < 3:
        raise ValueError(
            f"Not enough customers with 2+ orders (found {n_samples}, need at least 3) "
            "to perform K-Means clustering."
        )

    numeric_features = ["order_frequency", "avg_spend", "recency_days", "total_items", "avg_items_per_order"]
    categorical_features = ["top_category"]
    features_cols = numeric_features + categorical_features

    X = df_features[features_cols]

    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        ]
    )

    X_preprocessed = preprocessor.fit_transform(X)

    # Determine range of k
    # We want 3 to 6, but silhouette score requires 2 <= k <= n_samples - 1
    max_k = min(6, n_samples - 1)
    min_k = min(3, max_k)
    if min_k < 2:
        min_k = 2

    if min_k > max_k:
        # If still invalid, force k=2 and skip silhouette optimization
        best_k = 2
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_preprocessed)
        best_model = kmeans
        best_score = float(silhouette_score(X_preprocessed, labels)) if n_samples > 2 else 0.0
    else:
        best_k = min_k
        best_score = -1.0
        best_model = None

        for k in range(min_k, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X_preprocessed)
            score = float(silhouette_score(X_preprocessed, labels))
            
            if score > best_score:
                best_score = score
                best_k = k
                best_model = kmeans

    # Assign personas dynamically based on cluster characteristics
    labels = best_model.labels_
    centroids = []
    for cluster_id in range(best_k):
        cluster_customers = df_features[labels == cluster_id]
        centroids.append({
            "cluster_id": cluster_id,
            "avg_spend": float(cluster_customers["avg_spend"].mean()),
            "order_frequency": float(cluster_customers["order_frequency"].mean()),
            "recency_days": float(cluster_customers["recency_days"].mean()),
            "avg_items_per_order": float(cluster_customers["avg_items_per_order"].mean()),
        })

    # 1. At-Risk: Cluster with highest average recency_days
    sorted_by_recency = sorted(centroids, key=lambda x: x["recency_days"], reverse=True)
    at_risk_cluster = sorted_by_recency[0]["cluster_id"]

    # Remove at-risk from remaining pools
    remaining = [c for c in centroids if c["cluster_id"] != at_risk_cluster]

    # 2. VIP Regular: Out of remaining, highest avg_spend * order_frequency
    if remaining:
        sorted_by_vip = sorted(remaining, key=lambda x: x["avg_spend"] * x["order_frequency"], reverse=True)
        vip_cluster = sorted_by_vip[0]["cluster_id"]
        remaining = [c for c in remaining if c["cluster_id"] != vip_cluster]
    else:
        vip_cluster = -1

    # 3. Big Spender: Out of remaining, highest avg_spend
    if remaining:
        sorted_by_spend = sorted(remaining, key=lambda x: x["avg_spend"], reverse=True)
        big_spender_cluster = sorted_by_spend[0]["cluster_id"]
        remaining = [c for c in remaining if c["cluster_id"] != big_spender_cluster]
    else:
        big_spender_cluster = -1

    # 4. Occasional Visitor: Remaining clusters
    occasional_clusters = [c["cluster_id"] for c in remaining]

    cluster_to_persona = {}
    cluster_to_persona[at_risk_cluster] = "At-Risk"
    if vip_cluster != -1:
        cluster_to_persona[vip_cluster] = "VIP Regular"
    if big_spender_cluster != -1:
        cluster_to_persona[big_spender_cluster] = "Big Spender"
    for c_id in occasional_clusters:
        cluster_to_persona[c_id] = "Occasional Visitor"

    # Save model data using manifest_helper
    from app.ml.manifest_helper import get_next_version, update_manifest

    if version is None:
        version = get_next_version(tenant_id, "segmentation")

    filename = f"segments_v{version}.pkl"
    model_path = os.path.join(model_dir, str(tenant_id), filename)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    model_data = {
        "preprocessor": preprocessor,
        "model": best_model,
        "cluster_to_persona": cluster_to_persona,
        "features_cols": features_cols
    }
    
    joblib.dump(model_data, model_path)
    
    # Update manifest
    update_manifest(tenant_id, "segmentation", filename, reason=reason)
    
    return {
        "status": "success",
        "best_k": best_k,
        "silhouette_score": best_score,
        "cluster_to_persona": cluster_to_persona,
        "model_path": model_path,
        "version": version
    }
