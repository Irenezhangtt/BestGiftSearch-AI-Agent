from __future__ import annotations

import math
import re

from .models import Product, Recommendation, SearchIntent


PRODUCTS = [
    Product(id="coffee-kit", name="Global Coffee Tasting Kit", description="Single-origin beans and guided tasting cards from four regions.", category="food", interests=["coffee", "travel", "food"], price=54, shipping={"US": 6, "CA": 10, "GB": 12}, url="https://example.com/gifts/coffee-kit", image="https://images.unsplash.com/photo-1442512595331-e89e73853f31?auto=format&fit=crop&w=900&q=80", merchant="Atlas & Oak", rating=4.8),
    Product(id="travel-journal", name="Personalized Travel Journal", description="Recycled leather journal with custom initials and trip prompts.", category="personalized", interests=["travel", "writing", "art"], price=42, shipping={"US": 5, "CA": 8, "GB": 7}, url="https://example.com/gifts/travel-journal", image="https://images.unsplash.com/photo-1517842645767-c639042777db?auto=format&fit=crop&w=900&q=80", merchant="Paper Voyage", rating=4.7),
    Product(id="indoor-garden", name="Smart Indoor Herb Garden", description="Countertop grow light and self-watering planter for six herbs.", category="home", interests=["gardening", "cooking", "technology"], price=79, shipping={"US": 0, "CA": 14, "GB": 18}, url="https://example.com/gifts/indoor-garden", image="https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=900&q=80", merchant="Sprout Lab", rating=4.6),
    Product(id="night-sky", name="Custom Night Sky Print", description="Museum-grade print of the stars from a meaningful date and place.", category="personalized", interests=["art", "astronomy", "romance"], price=38, shipping={"US": 7, "CA": 9, "GB": 6}, url="https://example.com/gifts/night-sky", image="https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=80", merchant="Celestial Studio", rating=4.9),
    Product(id="picnic-pack", name="Packable Picnic Blanket", description="Water-resistant recycled-fabric blanket that folds into a travel tote.", category="outdoors", interests=["travel", "outdoors", "hiking"], price=48, shipping={"US": 4, "CA": 9, "GB": 11}, url="https://example.com/gifts/picnic-pack", image="https://images.unsplash.com/photo-1526392060635-9d6019884377?auto=format&fit=crop&w=900&q=80", merchant="Roam Good", rating=4.5),
    Product(id="tea-ceremony", name="Japanese Tea Ceremony Set", description="Hand-glazed bowl, whisk, scoop, matcha, and a concise ritual guide.", category="food", interests=["tea", "mindfulness", "culture"], price=68, shipping={"US": 8, "CA": 12, "GB": 15}, url="https://example.com/gifts/tea-ceremony", image="https://images.unsplash.com/photo-1564890369478-c89ca6d9cde9?auto=format&fit=crop&w=900&q=80", merchant="Still House", rating=4.8),
    Product(id="lego-bot", name="Build-Your-Own Robot Kit", description="Screen-free programmable robot with progressive family challenges.", category="technology", interests=["technology", "science", "family"], price=72, shipping={"US": 0, "CA": 11, "GB": 13}, url="https://example.com/gifts/robot-kit", image="https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=900&q=80", merchant="Bright Circuit", rating=4.7),
    Product(id="vinyl-sub", name="Three-Month Vinyl Discovery Club", description="Curated records matched to a listening profile, with liner notes.", category="subscription", interests=["music", "collecting", "art"], price=75, shipping={"US": 0, "CA": 15, "GB": 16}, url="https://example.com/gifts/vinyl-club", image="https://images.unsplash.com/photo-1461360228754-6e81c478b882?auto=format&fit=crop&w=900&q=80", merchant="Needle Drop", rating=4.6),
]


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def retrieve(intent: SearchIntent, products: list[Product] | None = None, limit: int = 8) -> list[Product]:
    query = tokenize(" ".join([intent.recipient, intent.occasion, *intent.interests]))
    corpus = products or PRODUCTS
    def relevance(product: Product) -> float:
        words = tokenize(" ".join([product.name, product.description, product.category, *product.interests]))
        overlap = len(query & words) / math.sqrt(max(1, len(query) * len(words)))
        phrase = sum(0.08 for interest in intent.interests if interest in product.interests)
        afford = 0.25 if product.price <= intent.budget else -0.3
        return overlap + phrase + afford + product.rating / 100
    return sorted(corpus, key=relevance, reverse=True)[:limit]


def rank(products: list[Product], intent: SearchIntent, preferences: list[str]) -> list[Recommendation]:
    wanted = tokenize(" ".join([*intent.interests, *preferences]))
    excluded = tokenize(" ".join(intent.exclusions))
    results = []
    for product in products:
        shipping = product.shipping.get(intent.country, 22)
        total = product.price + shipping
        product_words = tokenize(" ".join([product.name, product.description, *product.interests]))
        matches = sorted(wanted & product_words)
        conflict = sorted(excluded & product_words)
        budget_score = max(0, 1 - total / max(intent.budget, 1))
        interest_score = min(1, len(matches) / max(1, len(wanted)))
        score = round(100 * (0.5 * interest_score + 0.3 * budget_score + 0.2 * product.rating / 5), 1)
        if conflict:
            score -= 35
        reasons = ([f"Matches {', '.join(matches)}"] if matches else ["A versatile, well-reviewed gift"]) + [f"{intent.currency} {total:.0f} delivered", f"Rated {product.rating}/5"]
        caveat = None if total <= intent.budget else f"Exceeds the {intent.currency} {intent.budget:.0f} budget by {intent.currency} {total-intent.budget:.0f}"
        results.append(Recommendation(product=product, shipping_cost=shipping, total_cost=total, score=max(0, score), reasons=reasons, caveat=caveat))
    return sorted(results, key=lambda item: item.score, reverse=True)[:4]
