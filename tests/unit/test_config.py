from pyjpx_etf.config import Config, config


class TestConfig:
    def test_defaults(self):
        c = Config()
        assert c.timeout == 30
        assert c.request_delay == 0.0
        assert len(c.provider_urls) == 2

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
