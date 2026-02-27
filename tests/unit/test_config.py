import pytest

from pyjpx_etf.config import Config, _ALIASES, config


class TestConfig:
    def test_defaults(self):
        c = Config()
        assert c.timeout == 30
        assert c.request_delay == 0.0
        assert len(c.provider_urls) == 2
        assert c.lang == "ja"

    def test_mutation(self):
        c = Config()
        c.timeout = 60
        c.request_delay = 0.5
        assert c.timeout == 60
        assert c.request_delay == 0.5

    def test_module_level_config_exists(self):
        assert isinstance(config, Config)

    def test_provider_urls_contain_placeholder(self):
        c = Config()
        for url in c.provider_urls:
            assert "{code}" in url

    def test_lang_valid_values(self):
        c = Config()
        c.lang = "en"
        assert c.lang == "en"
        c.lang = "ja"
        assert c.lang == "ja"

    def test_lang_invalid_raises(self):
        c = Config()
        with pytest.raises(ValueError, match="lang must be one of"):
            c.lang = "fr"


class TestAliases:
    def test_aliases_is_dict(self):
        assert isinstance(_ALIASES, dict)

    def test_all_aliases_present(self):
        expected = {
            "topix", "225", "core30", "div50", "div70", "div100",
            "pbr", "fang", "sox", "jpsox1", "jpsox2",
        }
        assert expected == set(_ALIASES.keys())

    def test_alias_values_are_strings(self):
        for code in _ALIASES.values():
            assert isinstance(code, str)
