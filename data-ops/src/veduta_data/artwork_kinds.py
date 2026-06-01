from __future__ import annotations

ARTWORK_KIND_FLAT_ART = "flat-art"
ARTWORK_KIND_PHOTOGRAPHY = "photography"
ARTWORK_KIND_STREET_ART = "street-art"
ARTWORK_KIND_OBJECT_OR_DOCUMENT = "object-or-document"
ARTWORK_KIND_OTHER = "other"

STREET_ART_COLLECTION_IDS = {"east-side", "graffitimundo"}

PHOTOGRAPHY_CREATORS = [
    "alexander gardner",
    "alfred stieglitz",
    "ansel adams",
    "berenice abbott",
    "carleton watkins",
    "dorothea lange",
    "eadweard muybridge",
    "edward s curtis",
    "gustave le gray",
    "laura gilpin",
    "lewis hine",
    "lewis wickes hine",
    "man ray",
    "mathew brady",
    "paul strand",
    "timothy o sullivan",
    "walker evans",
    "william henry jackson",
]

PHOTOGRAPHY_TITLE_TERMS = [
    "albumen print",
    "daguerreotype",
    "gelatin silver",
    "photograph",
]

OBJECT_OR_DOCUMENT_TITLE_TERMS = [
    "bowl",
    "carpet",
    "chart",
    "cup with",
    "dish",
    "document",
    "ewer",
    "fragment",
    "jar",
    "letter",
    "manuscript",
    "map of",
    "page from",
    "perspective map",
    "plate",
    "rug",
    "textile",
    "vase",
    "wall fragment",
    "wine cistern",
]


def classify_artwork_kind(collection_id: str, title: str, creator: str) -> str:
    if collection_id in STREET_ART_COLLECTION_IDS:
        return ARTWORK_KIND_STREET_ART

    normalized_creator = normalize(creator)
    if contains_any(PHOTOGRAPHY_CREATORS, normalized_creator):
        return ARTWORK_KIND_PHOTOGRAPHY

    normalized_title = normalize(title)
    if contains_any(PHOTOGRAPHY_TITLE_TERMS, normalized_title):
        return ARTWORK_KIND_PHOTOGRAPHY

    if contains_any(OBJECT_OR_DOCUMENT_TITLE_TERMS, normalized_title):
        return ARTWORK_KIND_OBJECT_OR_DOCUMENT

    return ARTWORK_KIND_FLAT_ART


def contains_any(terms: list[str], value: str) -> bool:
    return any(term in value for term in terms)


def normalize(value: str) -> str:
    return value.casefold().replace(".", " ").replace("’", "'")
