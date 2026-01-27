from tui.core.router import parse_route


def test_parse_route_home():
    assert parse_route("").kind == "home"
    assert parse_route("/").kind == "home"
    assert parse_route("home").kind == "home"


def test_parse_route_profile():
    route = parse_route("profile/liquidation")
    assert route.kind == "profile"
    assert route.name == "liquidation"


def test_parse_route_view():
    route = parse_route("views/time")
    assert route.kind == "view"
    assert route.name == "time"
