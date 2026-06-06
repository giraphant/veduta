from __future__ import annotations

import re

ARTWORK_KIND_FLAT_ART = "flat-art"
ARTWORK_KIND_PHOTOGRAPHY = "photography"
ARTWORK_KIND_STREET_ART = "street-art"
ARTWORK_KIND_OBJECT_OR_DOCUMENT = "object-or-document"
ARTWORK_KIND_OTHER = "other"

STREET_ART_COLLECTION_IDS = {"east-side", "graffitimundo"}

STREET_ART_CREATORS = [
    "aiko",
    "alice pasquini",
    "arm collective",
    "cabaio",
    "daleast",
    "do art foundation",
    "icy & sot",
    "kilt and vhils",
    "okuda",
    "saaret yoseph",
    "seth",
    "stik",
    "street artist known as tk deol",
    "vhils",
]

ARTWORK_KIND_OVERRIDES = {
    ("albany", "joseph-hall-albany-ny-silver-trade-armbands"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "ani-o-neill-there-s-no-place-like-home"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "ani-o-neill-there-s-no-place-like-home-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "bill-culbert-flat-out"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "bill-culbert-flat-out-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-attributed-to-jacques-dubois-chest-of-drawers"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-attributed-to-jacques-dubois-chest-of-drawers-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-derby-porcelain-manufactory-william-duesbury-co-derby-derbyshire-operated-about-1748-1848-four-quarters-of-the-globe"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-derby-porcelain-manufactory-william-duesbury-co-derby-derbyshire-operated-about-1748-1848-four-quarters-of-the-globe-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-unknown-artist-guanacaste-nicoya-zone-pacific-coast-ceremonial-bird-effigy-grinding-stone"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "by-unknown-artist-guanacaste-nicoya-zone-pacific-coast-ceremonial-bird-effigy-grinding-stone-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "et-al-simultaneous-invalidations-second-attempt"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "et-al-simultaneous-invalidations-second-attempt-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "frances-hodgkins-spanish-shrine"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "frances-hodgkins-spanish-shrine-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "francis-upritchard-jealous-saboteurs"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "francis-upritchard-jealous-saboteurs-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "judy-darragh-rock-and-rose-bed"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "judy-darragh-rock-and-rose-bed-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "ronnie-van-hout-psycho"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "ronnie-van-hout-psycho-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "w-d-hammond-giant-eagle"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("berlin", "w-d-hammond-giant-eagle-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "alexander-proctor-panther"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "augustus-saint-gaudens-robert-louis-stevenson"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-bull-bawling"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-dinner-time"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-mountain-mother"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-oh-mother-what-is-it"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-smoking-with-the-spirit-of-the-buffalo"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-smoking-with-the-spirit-of-the-buffalo-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-the-bluffers"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-the-range-father"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-the-snake-priest"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "charles-m-russell-the-texas-steer"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "david-johnson-oak"): ARTWORK_KIND_PHOTOGRAPHY,
    ("carter", "george-bellows-the-pool-player"): ARTWORK_KIND_PHOTOGRAPHY,
    ("carter", "james-gilchrist-benton-harper-s-ferry-virginia"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("carter", "unknown-photographer-four-women-in-ribbon-striped-dresses"): ARTWORK_KIND_PHOTOGRAPHY,
    ("carter", "unknown-photographer-portraits-of-women"): ARTWORK_KIND_PHOTOGRAPHY,
    ("chicago", "ancient-egyptian-stela-of-amenemhat-and-hemet"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "adler-sullivan-architects-chicago-stock-exchange-trading-room-reconstruction-at-the-art-institute-of-chicago"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "edward-clark-potter-sleeping-infant-faun-visited-by-an-inquisitive-rabbit"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "france-fan"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "leonard-wells-volk-life-cast-of-the-hands-and-face-of-abraham-lincoln"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "narcissa-niblack-thorne-e-10-english-dining-room-of-the-georgian-period-1770-90"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "neapolitan-creche"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("chicago", "spanish-retable-and-frontal-of-the-life-of-christ-and-the-virgin"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("essentials", "suiko-scorpion"): ARTWORK_KIND_STREET_ART,
    ("tokyo", "unknown-vessel-in-shape-of-bronze-ding-green-glaze"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "callum-morton-motormouth"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "christo-package"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "christo-packed-coast-one-million-square-feet-project"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "christo-two-wrapped-trees"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "doris-salcedo-atrabiliarios"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "francis-alys-untitled"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "francis-alys-untitled-2"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "francis-alys-untitled-3"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "hossein-valamanesh-middle-path"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "janet-laurence-in-stance-of-memory"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "jannis-kounellis-untitled-1984-87"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "mike-parr-bronze-liars"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "ralph-balson-abstraction"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "richard-long-southern-gravity"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "richard-bell-pay-the-rent"): ARTWORK_KIND_PHOTOGRAPHY,
    ("wales", "septimus-power-the-enemy-in-sight"): ARTWORK_KIND_PHOTOGRAPHY,
    ("wales", "sol-lewitt-three-part-variations-on-three-different-kinds"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "ugo-rondinone-if-there-were-anywhere-but-desert-wednesday"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
    ("wales", "ugo-rondinone-what-do-you-want"): ARTWORK_KIND_OBJECT_OR_DOCUMENT,
}

DOCUMENT_CREATORS = [
    "albert ruger",
    "augustus koch",
    "eli sheldon glover",
    "henry wellge",
    "thaddeus mortimer fowler",
]

PHOTOGRAPHY_CREATORS = [
    "alexander gardner",
    "alfred stieglitz",
    "ansel adams",
    "berenice abbott",
    "carleton watkins",
    "dorothea lange",
    "eadweard muybridge",
    "edward s curtis",
    "eliot porter",
    "erwin e smith",
    "gustave le gray",
    "laura gilpin",
    "lewis hine",
    "lewis wickes hine",
    "man ray",
    "marion post wolcott",
    "mathew brady",
    "paul strand",
    "samuel j miller",
    "timothy h o'sullivan",
    "timothy o sullivan",
    "walker evans",
    "william henry jackson",
]

PHOTOGRAPHY_TITLE_TERMS = [
    "albumen print",
    "daguerreotype",
    "gelatin silver",
]

PHOTOGRAPHY_TITLE_PATTERNS = [
    r"\bphotographs?\b",
]

PHOTOGRAPHY_DETAIL_TERMS = [
    "albumen print",
    "daguerreotype",
    "gelatin silver",
    "photograph",
    "photographs",
    "photogravure",
    "salted paper print",
]

DOCUMENT_TITLE_PATTERNS = [
    r"\bcarpet\b",
    r"\bchart\b",
    r"\bdocument\b",
    r"\bletter\b",
    r"\bmanuscript\b",
    r"\bmap of\b",
    r"\bpage from\b",
    r"\bbirds?(?:'?s)?[- ]eye view\b",
    r"\bpanoramic birds?(?:'?s)?[- ]eye view\b",
    r"\bperspective map\b",
    r"\brug\b",
    r"\btextile\b",
]

OBJECT_TITLE_PATTERNS = [
    "covered cup",
    "casket",
    "cravat",
    "easter egg",
    "dress fabric",
    "fabric",
    "fish plate",
    "drinking cup",
    "articulated dragon",
    "bobbins",
    "liquor jar",
    "mural fragment",
    "red-figure",
    "reliquary box",
    "reliquary casket",
    "ritual cache",
    "piano",
    "tea and coffee service",
    "tea bowl",
    "vessel",
    "sculpture",
    "storage jar",
    "table, painted earthenware",
    "teapot",
    "wall fragment",
    "writing box",
    "wine cistern",
    r"\bbox\b",
    r"\bcabinet\b",
    r"\bbowl with\b",
    r"\bcup with\b",
    r"\bewer\b",
    r"\bjar with\b",
    r"\bvase\b$",
]

FLAT_ART_TITLE_PATTERNS = [
    "bouquet of flowers",
    "bowl of citrons",
    "collector's cabinet",
    "dish of apples",
    "flowers in a",
    "seated beside a vase",
    "sketch",
    "still life",
    "studies",
]

FLAT_ART_DETAIL_TERMS = [
    "drawing",
    "drawings",
    "engraving",
    "etching",
    "lithograph",
    "painting",
    "paintings",
    "print",
    "prints",
    "sketch",
    "watercolor",
    "watercolour",
    "woodcut",
]

OBJECT_DETAIL_TERMS = [
    "ceramic",
    "ceramics",
    "costume",
    "dress",
    "fabric",
    "furniture",
    "glass",
    "jewellery",
    "jewelry",
    "metalwork",
    "silver",
    "sculpture",
    "textile",
    "vessel",
]


def classify_artwork_kind(
    collection_id: str,
    title: str,
    creator: str,
    metadata: dict[str, object] | None = None,
    artwork_id: str | None = None,
) -> str:
    if artwork_id is not None and (collection_id, artwork_id) in ARTWORK_KIND_OVERRIDES:
        return ARTWORK_KIND_OVERRIDES[(collection_id, artwork_id)]
    if collection_id in STREET_ART_COLLECTION_IDS:
        return ARTWORK_KIND_STREET_ART
    normalized_creator = normalize(creator)
    if contains_any(STREET_ART_CREATORS, normalized_creator):
        return ARTWORK_KIND_STREET_ART
    if contains_any(DOCUMENT_CREATORS, normalized_creator):
        return ARTWORK_KIND_OBJECT_OR_DOCUMENT
    if contains_any(PHOTOGRAPHY_CREATORS, normalized_creator):
        return ARTWORK_KIND_PHOTOGRAPHY
    normalized_title = normalize(title)
    normalized_metadata = normalize_metadata(metadata or {})
    combined_details = " ".join(normalized_metadata.values())
    if matches_any(DOCUMENT_TITLE_PATTERNS, normalized_title):
        return ARTWORK_KIND_OBJECT_OR_DOCUMENT
    if contains_any(PHOTOGRAPHY_TITLE_TERMS, normalized_title):
        return ARTWORK_KIND_PHOTOGRAPHY
    if matches_any(PHOTOGRAPHY_TITLE_PATTERNS, normalized_title):
        return ARTWORK_KIND_PHOTOGRAPHY
    if contains_any(PHOTOGRAPHY_DETAIL_TERMS, combined_details):
        return ARTWORK_KIND_PHOTOGRAPHY
    if matches_any(FLAT_ART_TITLE_PATTERNS, normalized_title):
        return ARTWORK_KIND_FLAT_ART
    if matches_any(OBJECT_TITLE_PATTERNS, normalized_title):
        return ARTWORK_KIND_OBJECT_OR_DOCUMENT
    if contains_any(FLAT_ART_DETAIL_TERMS, combined_details):
        return ARTWORK_KIND_FLAT_ART
    if contains_any(OBJECT_DETAIL_TERMS, combined_details):
        return ARTWORK_KIND_OBJECT_OR_DOCUMENT
    return ARTWORK_KIND_FLAT_ART


def contains_any(terms: list[str], value: str) -> bool:
    return any(term in value for term in terms)


def matches_any(patterns: list[str], value: str) -> bool:
    return any(re.search(pattern, value) for pattern in patterns)


def normalize(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_tags.casefold().replace(".", " ").replace("’", "'")).strip()


def normalize_metadata(metadata: dict[str, object]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in metadata.items():
        if isinstance(value, list):
            normalized[key] = normalize(" ".join(str(item) for item in value))
        elif value is not None:
            normalized[key] = normalize(str(value))
    return normalized
