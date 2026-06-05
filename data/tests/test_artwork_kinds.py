from veduta_data.artwork_kinds import classify_artwork_kind


def test_classifies_street_art_collections():
    assert classify_artwork_kind("graffitimundo", "Mural", "Blu") == "street-art"


def test_classifies_street_art_by_creator():
    assert classify_artwork_kind("shizuoka", "AIKO HANAKO'S DANCE", "AIKO") == "street-art"
    assert classify_artwork_kind("essentials", "The Guardian Angel", "Stik") == "street-art"
    assert classify_artwork_kind("essentials", "Remed and Okuda London 2014", "Okuda") == "street-art"


def test_classifies_photography_by_creator_and_title():
    assert classify_artwork_kind("essentials", "Moonrise", "Ansel Adams") == "photography"
    assert classify_artwork_kind("essentials", "Untitled gelatin silver print", "Unknown") == "photography"
    assert classify_artwork_kind("carter", "Couverville Island, Antarctica, January 1975", "Eliot Porter") == "photography"


def test_does_not_classify_photographer_word_as_photography():
    assert classify_artwork_kind("wales", "An unknown photographer", "Unknown artist") == "flat-art"


def test_classifies_object_or_document_by_title():
    assert classify_artwork_kind("smithsonian", "Map of the Mississippi", "Unknown") == "object-or-document"
    assert classify_artwork_kind("carter", "Bird's Eye View of Louisville, Kentucky, 1876.", "Albert Ruger") == "object-or-document"
    assert classify_artwork_kind("tokyo", "Bowl with Design of Dragon and Waves", "Jing-de-zhen Ware") == "object-or-document"
    assert classify_artwork_kind("cleveland", "Writing Box (Suzuribako) with Phoenix in Paulownia", "Unknown") == "object-or-document"
    assert classify_artwork_kind("chicago", "Cabinet", "Herter Brothers") == "object-or-document"


def test_title_object_words_do_not_override_still_life_paintings():
    assert classify_artwork_kind("essentials", "Still Life with Bowl of Citrons", "Giovanna Garzoni") == "flat-art"
    assert classify_artwork_kind("met", "Bouquet of Flowers in a Vase", "Vincent van Gogh") == "flat-art"
    assert classify_artwork_kind("essentials", "The Archdukes Albert and Isabella Visiting a Collector's Cabinet", "Hieronymus II Francken") == "flat-art"
    assert classify_artwork_kind("essentials", "A Gentleman’s Table", "Claude Raguet Hirst") == "flat-art"


def test_word_boundaries_avoid_false_object_matches():
    assert classify_artwork_kind("rijksmuseum", "Brug bij de Marepoort te Leiden", "Abraham Rademaker") == "flat-art"


def test_metadata_can_classify_flat_art_before_weak_object_terms():
    assert classify_artwork_kind(
        "vam",
        "View of Florence from the South West",
        "Francesco Rosselli",
        {"objectType": "Painting", "medium": "Tempera and oil on panel"},
    ) == "flat-art"


def test_manual_artwork_overrides_handle_visual_audit_findings():
    assert classify_artwork_kind(
        "carter",
        "[Portraits of women]",
        "Unknown photographer",
        artwork_id="unknown-photographer-portraits-of-women",
    ) == "photography"
    assert classify_artwork_kind(
        "tokyo",
        "Vessel in Shape of Bronze Ding, Green Glaze",
        "unknown",
        artwork_id="unknown-vessel-in-shape-of-bronze-ding-green-glaze",
    ) == "object-or-document"
    assert classify_artwork_kind(
        "carter",
        "The Bluffers",
        "Charles M. Russell",
        artwork_id="charles-m-russell-the-bluffers",
    ) == "object-or-document"
    assert classify_artwork_kind(
        "chicago",
        "Retable and Frontal of the Life of Christ and the Virgin",
        "Spanish",
        artwork_id="spanish-retable-and-frontal-of-the-life-of-christ-and-the-virgin",
    ) == "object-or-document"
    assert classify_artwork_kind(
        "albany",
        "Silver Trade Armbands",
        "Joseph Hall, Albany, NY",
        artwork_id="joseph-hall-albany-ny-silver-trade-armbands",
    ) == "object-or-document"


def test_defaults_to_flat_art():
    assert classify_artwork_kind("essentials", "Water Lilies", "Claude Monet") == "flat-art"
