from candidate_transformer.normalizers import Normalizer


def test_phone_normalization_to_e164():
    result = Normalizer(default_region="US").normalize_phone("(415) 555-0134")

    assert result.value == "+14155550134"
    assert result.warning is None


def test_invalid_phone_returns_warning():
    result = Normalizer(default_region="US").normalize_phone("123")

    assert result.value is None
    assert result.warning == "invalid phone number"


def test_skill_normalization_uses_alias_dictionary():
    normalizer = Normalizer()

    assert normalizer.normalize_skill("py") == "Python"
    assert normalizer.normalize_skill("Postgres") == "PostgreSQL"


def test_unknown_country_is_not_invented_or_crashed():
    city, region, country = Normalizer().split_location("Gotham, ZZ, Neverland")

    assert city == "Gotham"
    assert region == "ZZ"
    assert country is None
