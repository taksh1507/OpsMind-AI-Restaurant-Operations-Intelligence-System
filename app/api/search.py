"""Global search endpoint for menu items, categories, and staff.

Implements fuzzy search across the database with real-time filtering.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from difflib import SequenceMatcher

from app.api.deps import get_db
from app.models.base import Base
from app.models.menu import MenuItem, Category
from app.models.staff import Staff

router = APIRouter(prefix="/search", tags=["search"])


def fuzzy_match(query: str, target: str, threshold: float = 0.6) -> float:
    """Calculate fuzzy match score between query and target string.
    
    Args:
        query: Search query
        target: Target string to match against
        threshold: Minimum score to consider a match
        
    Returns:
        Match score between 0 and 1
    """
    query_lower = query.lower()
    target_lower = target.lower()

    # Exact match or substring match gets highest score
    if query_lower in target_lower:
        return 0.9 + (len(query_lower) / len(target_lower)) * 0.1

    # Use SequenceMatcher for fuzzy matching
    ratio = SequenceMatcher(None, query_lower, target_lower).ratio()
    return ratio


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
):
    """Perform global fuzzy search across menu items, categories, and staff.

    Args:
        q: Search query string
        db: Database session

    Returns:
        List of search results with category information
    """
    threshold = 0.5
    results = []

    try:
        # Search menu items
        menu_query = select(MenuItem).limit(50)
        menu_result = await db.execute(menu_query)
        menu_items = menu_result.scalars().all()

        for item in menu_items:
            score = fuzzy_match(q, item.name, threshold)
            if score >= threshold:
                results.append({
                    "id": str(item.id),
                    "name": item.name,
                    "category": "menu",
                    "description": f"${item.price:.2f}" if hasattr(item, 'price') and item.price else "Menu Item",
                    "score": score,
                })

        # Search categories
        category_query = select(Category).limit(50)
        category_result = await db.execute(category_query)
        categories = category_result.scalars().all()

        for category in categories:
            score = fuzzy_match(q, category.name, threshold)
            if score >= threshold:
                results.append({
                    "id": str(category.id),
                    "name": category.name,
                    "category": "category",
                    "description": f"{category.items_count if hasattr(category, 'items_count') else 0} items",
                    "score": score,
                })

        # Search staff
        staff_query = select(Staff).limit(50)
        staff_result = await db.execute(staff_query)
        staff_members = staff_result.scalars().all()

        for member in staff_members:
            # Search by name
            score = fuzzy_match(q, member.name, threshold)
            if score >= threshold:
                results.append({
                    "id": str(member.id),
                    "name": member.name,
                    "category": "staff",
                    "description": getattr(member, 'position', 'Staff Member'),
                    "score": score,
                })

            # Also search by position/role if available
            if hasattr(member, 'position') and member.position:
                score_pos = fuzzy_match(q, member.position, threshold)
                if score_pos >= threshold:
                    results.append({
                        "id": str(member.id),
                        "name": member.name,
                        "category": "staff",
                        "description": getattr(member, 'position', 'Staff Member'),
                        "score": score_pos,
                    })

        # Sort by relevance score (descending)
        results.sort(key=lambda x: x["score"], reverse=True)

        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for result in results:
            key = (result['category'], result['id'])
            if key not in seen:
                seen.add(key)
                unique_results.append({
                    "id": result["id"],
                    "name": result["name"],
                    "category": result["category"],
                    "description": result.get("description"),
                })

        return {
            "query": q,
            "count": len(unique_results),
            "results": unique_results[:20],  # Limit to top 20 results
        }

    except Exception as e:
        # Log error but don't expose internal details
        print(f"Search error: {str(e)}")
        return {
            "query": q,
            "count": 0,
            "results": [],
            "error": "Search temporarily unavailable",
        }
