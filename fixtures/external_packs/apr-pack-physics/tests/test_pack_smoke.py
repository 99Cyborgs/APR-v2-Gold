from apr_pack_physics.entry import build_pack


def test_build_pack():
    pack = build_pack()
    assert pack.pack_id == "physics_pack"
    assert pack.advisory_only is True
