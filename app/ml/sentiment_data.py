"""Sentiment Data Preparation Pipeline.

Prepares training data to bootstrap a local sentiment classifier, merging
restaurant database reviews, cached external Yelp/Kaggle dataset reviews,
and combinatoric synthetic reviews, and weak-labels them.
"""

import os
import io
import csv
import math
import random
import urllib.request
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.review import Review
from app.services.ai_agent import AIConsultant, process_review

# Predefined food items, staff descriptions, and sentiment templates for combinatoric generation
FOODS = [
    "butter chicken", "pizza", "pasta", "burger", "cacio e pepe", "garlic naan",
    "pepperoni pizza", "margherita pizza", "truffle burger", "carbonara",
    "seafood linguine", "caesar salad", "grilled shrimp salad", "bruschetta",
    "calamari", "tiramisu", "panna cotta", "gelato", "butter naan", "paneer tikka"
]

STAFF = [
    "waiter", "staff", "service", "waitress", "server", "host", "manager", "team", "kitchen staff"
]

POSITIVE_TEMPLATES = [
    "The {food} was absolutely delicious and the {staff} was incredibly friendly.",
    "Best {food} I've had in a long time! Service was top-notch.",
    "Outstanding dinner tonight. The {food} was cooked to perfection and our waiter was very attentive.",
    "Great atmosphere and excellent {food}. Will definitely be back!",
    "Amazing experience. The {food} was delicious and the {staff} made us feel so welcome.",
    "A wonderful dining experience with great {food} and lovely service.",
    "Loved the {food}! Very fresh ingredients and beautiful presentation.",
    "High quality {food} and very friendly {staff}. Highly recommend this place!",
    "Outstanding food and excellent ambiance. The {food} was superb.",
    "Fantastic service and delightful food. The {food} exceeded expectations."
]

NEUTRAL_TEMPLATES = [
    "The {food} was decent, but the service was a bit slow.",
    "Average experience. The {food} was okay, nothing special.",
    "Nice atmosphere and okay {food}, but slightly overpriced.",
    "Good {food} but the seating was a bit cramped.",
    "The {food} was satisfactory, standard restaurant experience.",
    "Decent options for {food}, but the wait time was a bit long.",
    "Food was fine. Service was average. Nothing to write home about.",
    "The {food} was alright, but they were out of several menu items.",
    "The {food} was okay, and the {staff} was polite enough.",
    "Decent meal overall, the {food} was fine but nothing extraordinary."
]

NEGATIVE_TEMPLATES = [
    "The {food} was cold and the service was extremely slow.",
    "Very disappointed. The {food} was bland and tasteless.",
    "Worst experience. Our order was incorrect and the {staff} was rude.",
    "The noise level was way too high and the {food} was mediocre.",
    "Terrible customer service. Had to wait an hour for cold {food}.",
    "Not worth the price. Small portions and mediocre {food} quality.",
    "Avoid this place. The {food} made me feel sick and the service was poor.",
    "The service was poor and the {food} came out completely overcooked.",
    "Highly disappointed with the {food}. It was way too salty.",
    "The {food} was stale and the {staff} was not helpful at all."
]


def generate_single_synthetic_review(label: str) -> str:
    """Generate a single realistic restaurant review using combinatoric templates."""
    food = random.choice(FOODS)
    staff_member = random.choice(STAFF)
    
    if label == "positive":
        template = random.choice(POSITIVE_TEMPLATES)
    elif label == "negative":
        template = random.choice(NEGATIVE_TEMPLATES)
    else:
        template = random.choice(NEUTRAL_TEMPLATES)
        
    return template.format(food=food, staff=staff_member)


def get_heuristic_sentiment(text: str) -> tuple[str, float]:
    """Analyze review comment using a local keyword rule-based system.
    
    # TODO: replace heuristic with manual labeling once dataset exceeds 500 rows.
    """
    text_lower = text.lower()
    
    positive_words = {
        "delicious", "amazing", "best", "perfect", "outstanding", "great", 
        "excellent", "love", "wonderful", "friendly", "good", "fresh", 
        "incredible", "recommend", "top-notch", "nice", "fantastic", "tasty",
        "delightful", "superb", "awesome", "liked", "pleasant", "yummy"
    }
    
    negative_words = {
        "slow", "cold", "disappointed", "wrong", "bland", "worst", "unhappy", 
        "bad", "mediocre", "noise", "unbearable", "rude", "poor", "disappointing",
        "terrible", "avoid", "sick", "overcooked", "wait", "dry", "tasteless", 
        "awful", "horrible", "dirty", "salty", "stale", "slowest"
    }
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count == 0 and neg_count == 0:
        score = 0.0
    else:
        score = (pos_count - neg_count) / max(1, pos_count + neg_count)
        
    score = max(-1.0, min(1.0, round(score * 0.8, 2)))
    
    if score >= 0.3:
        label = "positive"
    elif score <= -0.3:
        label = "negative"
    else:
        label = "neutral"
        
    return label, score


async def weak_label_review(text: str) -> tuple[str, float]:
    """Call Gemini to weak-label review, falling back to local heuristic if key is missing or fails."""
    api_key = os.getenv("GEMINI_API_KEY") or (settings.gemini_api_key if hasattr(settings, "gemini_api_key") else None)
    if api_key:
        try:
            res = await process_review(text)
            if res.get("status") == "success":
                label = res.get("sentiment_label", "neutral")
                score = float(res.get("sentiment_score", 0.0))
                return label, score
        except Exception as e:
            print(f"Gemini weak-labeling call failed: {e}. Falling back to heuristic.")
            
    # Heuristic fallback
    # TODO: replace heuristic with manual labeling once dataset exceeds 500 rows.
    return get_heuristic_sentiment(text)


def download_public_dataset() -> pd.DataFrame:
    """Download a small restaurant reviews dataset from GitHub."""
    url = "https://raw.githubusercontent.com/sharmaroshan/Restaurant-Reviews-Analysis/master/Restaurant_Reviews.tsv"
    try:
        print(f"Attempting to download public Yelp/Kaggle restaurant reviews from: {url}")
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            tsv_data = response.read().decode('utf-8')
            
        df = pd.read_csv(io.StringIO(tsv_data), sep='\t')
        if 'Review' in df.columns and 'Liked' in df.columns:
            print(f"Successfully downloaded {len(df)} reviews.")
            mapped_records = []
            for _, row in df.iterrows():
                text = str(row['Review']).strip()
                liked = int(row['Liked'])
                label = "positive" if liked == 1 else "negative"
                score = 0.8 if liked == 1 else -0.8
                mapped_records.append({
                    "review_text": text,
                    "sentiment_label": label,
                    "sentiment_score": score
                })
            return pd.DataFrame(mapped_records)
    except Exception as e:
        print(f"Network download failed: {e}. Utilizing fallback combinatoric generator.")
    return pd.DataFrame()


def get_external_reviews() -> pd.DataFrame:
    """Get external dataset reviews. Uses local CSV cache if present, else downloads and caches."""
    cache_dir = "data"
    cache_path = os.path.join(cache_dir, "external_reviews.csv")
    
    if os.path.exists(cache_path):
        try:
            print(f"Loading cached external reviews from: {cache_path}")
            df = pd.read_csv(cache_path)
            if not df.empty and all(col in df.columns for col in ["review_text", "sentiment_label", "sentiment_score"]):
                return df
        except Exception as e:
            print(f"Error reading cached external reviews: {e}")
            
    # Cache miss
    df = download_public_dataset()
    if not df.empty:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            df.to_csv(cache_path, index=False)
            print(f"Cached external reviews to: {cache_path}")
        except Exception as e:
            print(f"Failed to cache external reviews: {e}")
    return df


async def build_raw_dataset(session: AsyncSession = None) -> pd.DataFrame:
    """Pull DB reviews, fetch/cache public reviews, and return raw DataFrame with labels."""
    db_reviews = []
    
    # 1. Pull reviews from provided session or connect to DB
    if session:
        try:
            stmt = select(Review)
            result = await session.execute(stmt)
            db_reviews = result.scalars().all()
        except Exception as e:
            print(f"Error querying reviews using provided session: {e}")
    else:
        try:
            db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
            if "sqlite" in settings.database_url and os.path.exists(db_path):
                engine = create_async_engine(settings.database_url, future=True)
                async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
                async with async_session() as new_session:
                    stmt = select(Review)
                    result = await new_session.execute(stmt)
                    db_reviews = result.scalars().all()
                await engine.dispose()
        except Exception as e:
            print(f"Error connecting to local DB file: {e}")
            
    raw_records = []
    
    # 2. Process database reviews
    if db_reviews:
        print(f"Found {len(db_reviews)} database reviews to weak-label.")
        for r in db_reviews:
            label, score = await weak_label_review(r.comment)
            raw_records.append({
                "review_text": r.comment,
                "sentiment_label": label,
                "sentiment_score": score
            })
    else:
        print("Database reviews table empty or missing. Seeding with synthetic review cases...")
        for _ in range(50):
            for label in ["positive", "neutral", "negative"]:
                comment = generate_single_synthetic_review(label)
                weak_lbl, score = await weak_label_review(comment)
                raw_records.append({
                    "review_text": comment,
                    "sentiment_label": weak_lbl,
                    "sentiment_score": score
                })
                
    # 3. Process external reviews
    ext_df = get_external_reviews()
    if not ext_df.empty:
        print(f"Merging with {len(ext_df)} external reviews.")
        for _, row in ext_df.iterrows():
            raw_records.append({
                "review_text": row["review_text"],
                "sentiment_label": row["sentiment_label"],
                "sentiment_score": row["sentiment_score"]
            })
    else:
        print("External reviews not available. Adding supplemental synthetic reviews to meet row counts...")
        for _ in range(100):
            for label in ["positive", "neutral", "negative"]:
                comment = generate_single_synthetic_review(label)
                weak_lbl, score = await weak_label_review(comment)
                raw_records.append({
                    "review_text": comment,
                    "sentiment_label": weak_lbl,
                    "sentiment_score": score
                })
                
    return pd.DataFrame(raw_records)


def balance_and_export(df: pd.DataFrame, output_path: str = "data/sentiment_train.csv") -> pd.DataFrame:
    """Enforces class balance and minimum row count, upsamples minority classes, and exports CSV."""
    if df.empty:
        raise ValueError("Cannot balance and export an empty DataFrame.")
        
    classes = ["positive", "negative", "neutral"]
    counts = {lbl: len(df[df["sentiment_label"] == lbl]) for lbl in classes}
    
    majority_class = max(counts, key=counts.get)
    majority_count = counts[majority_class]
    total_rows = len(df)
    
    if total_rows < 300 and majority_count < 100:
        # Scale all classes proportionally to reach 300
        factor = 300.0 / total_rows
        new_dfs = []
        for lbl in classes:
            lbl_df = df[df["sentiment_label"] == lbl]
            if not lbl_df.empty:
                target_count = math.ceil(len(lbl_df) * factor)
                new_dfs.append(lbl_df.sample(target_count, replace=True))
        df = pd.concat(new_dfs).reset_index(drop=True)
        counts = {lbl: len(df[df["sentiment_label"] == lbl]) for lbl in classes}
        majority_count = counts[majority_class]
        total_rows = len(df)
        
    # Enforce class balance and minimum row count of 300
    target_total = max(300, math.ceil(majority_count / 0.60))
    
    if total_rows < target_total:
        # Upsample only the minority classes to reach target_total
        remaining_needed = target_total - majority_count
        minority_classes = [lbl for lbl in classes if lbl != majority_class]
        
        # Divide remaining_needed among minority classes as evenly as possible
        minority_targets = {}
        for idx, lbl in enumerate(minority_classes):
            share = remaining_needed // len(minority_classes)
            if idx < (remaining_needed % len(minority_classes)):
                share += 1
            minority_targets[lbl] = share
            
        new_dfs = [df[df["sentiment_label"] == majority_class]]
        
        for lbl in minority_classes:
            lbl_df = df[df["sentiment_label"] == lbl]
            target_c = minority_targets[lbl]
            
            if not lbl_df.empty:
                # Upsample using sample with replacement
                upsampled_lbl_df = lbl_df.sample(target_c, replace=True)
                new_dfs.append(upsampled_lbl_df)
            else:
                # Synthesize if class is empty
                synthesized_records = []
                for _ in range(target_c):
                    comment = generate_single_synthetic_review(lbl)
                    lbl_weak, score = get_heuristic_sentiment(comment)
                    synthesized_records.append({
                        "review_text": comment,
                        "sentiment_label": lbl,
                        "sentiment_score": score
                    })
                new_dfs.append(pd.DataFrame(synthesized_records))
                
        df = pd.concat(new_dfs).reset_index(drop=True)
                
    # Final verification of count and constraints
    counts = df["sentiment_label"].value_counts().to_dict()
    total_rows = len(df)
    print("\nFinal Dataset Sentiment Distribution:")
    for label, count in counts.items():
        ratio = count / total_rows * 100.0
        print(f"  {label:<10}: {count} ({ratio:.2f}%)")
        
    # Write to target CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSuccessfully generated balanced dataset at: {output_path} ({len(df)} rows)")
    
    return df


async def main():
    print("==================================================")
    print("     SENTIMENT DATASET PREPARATION PIPELINE")
    print("==================================================")
    df = await build_raw_dataset()
    balance_and_export(df)
    print("==================================================\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
