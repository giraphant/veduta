from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceArtwork:
    id: str
    title: str
    creator: str
    attribution: str
    canonical_page: str
    artist_page: str | None
    upstream_image_base: str
    source_pack_id: int
    source_index: int
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceCollection:
    id: str
    source_pack_id: int
    short_name: str
    title: str
    expected_artwork_count: int
    source_sizes_mb: dict[str, int]
    artworks: list[SourceArtwork] = field(default_factory=list)


@dataclass(frozen=True)
class SourceLibrary:
    collections: list[SourceCollection]


def orientation_score(width: int, height: int, ratio_lo: float = 1.2, ratio_hi: float = 2.0) -> float:
    """Shared landscape-orientation bonus used by the museum importers."""
    if width <= height:
        return -4
    score = 8
    if ratio_lo <= width / max(height, 1) <= ratio_hi:
        score += 4
    return score


def usable_dimensions(width: int, height: int, min_long_edge: int) -> bool:
    """Shared wallpaper gate: long enough, landscape, aspect ratio 1.15-3.0."""
    if max(width, height) < min_long_edge:
        return False
    if width <= height:
        return False
    return 1.15 <= width / max(height, 1) <= 3.0
