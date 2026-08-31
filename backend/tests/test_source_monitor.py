from services.source_monitor import content_fingerprint


def test_source_fingerprint_is_stable_and_change_sensitive():
    first = content_fingerprint(b"authoritative source version one")
    assert first == content_fingerprint(b"authoritative source version one")
    assert first != content_fingerprint(b"authoritative source version two")
    assert len(first) == 64
