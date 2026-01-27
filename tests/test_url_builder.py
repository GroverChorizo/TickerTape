from tui.feeds.url_builder import EndpointUrlBuilder


def test_url_builder_endpoint_normalization():
    builder = EndpointUrlBuilder("https://api.moondev.com")
    assert (
        builder.build("price", symbol="btc") == "https://api.moondev.com/api/price/BTC"
    )
    assert (
        builder.build("orderbook", symbol="Eth")
        == "https://api.moondev.com/api/orderbook/ETH"
    )
    assert (
        builder.build("hip3_ticks", dex="hl", ticker="BTC")
        == "https://api.moondev.com/api/hip3_ticks/hl_btc.json"
    )
