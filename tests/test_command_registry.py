from tui.core.commands import CommandRegistry


def test_command_registry_help_filters_by_context():
    registry = CommandRegistry()
    registry.register("home", "Home command", lambda _c, _a: None, contexts=["home"])
    registry.register("global", "Global command", lambda _c, _a: None)
    registry.register("view", "View command", lambda _c, _a: None, contexts=["views"])

    home_help = registry.help_for("home")
    assert any("home" in line for line in home_help)
    assert any("global" in line for line in home_help)
    assert all("view" not in line for line in home_help)

    views_help = registry.help_for("views")
    assert any("view" in line for line in views_help)
    assert any("global" in line for line in views_help)
