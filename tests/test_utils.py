from etl_weather.utils import slugify


def test_slugify_basic():
    assert slugify("Bandung") == "bandung"
    assert slugify("Kota Yogyakarta") == "kota-yogyakarta"
    assert slugify("Cirebon/Harjamukti") == "cirebon-harjamukti"
    assert slugify("São Paulo") == "sao-paulo"
