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


@dataclass(frozen=True)
class SourceCollection:
    id: str
    source_pack_id: int
    short_name: str
    title: str
    expected_artwork_count: int
    expected_author_count: int
    source_sizes_mb: dict[str, int]
    artworks: list[SourceArtwork] = field(default_factory=list)


@dataclass(frozen=True)
class SourceLibrary:
    collections: list[SourceCollection]
