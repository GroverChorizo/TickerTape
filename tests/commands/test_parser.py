from __future__ import annotations

from commands.parser import CommandSpec, OptionSpec, parse_command


def test_parse_command_with_options_and_args():
    spec = CommandSpec(
        name="backtest",
        options=[
            OptionSpec(name="strategy", short="s", required=True),
            OptionSpec(name="data", short="d", required=True),
            OptionSpec(name="seed", short="S", required=False),
        ],
        min_args=1,
    )
    result = parse_command(
        spec,
        "backtest --strategy strat.py --data data.csv --seed 42 extra",
    )
    assert result.ok
    assert result.options["strategy"] == "strat.py"
    assert result.options["data"] == "data.csv"
    assert result.options["seed"] == "42"
    assert result.args == ["extra"]


def test_parse_command_unknown_option():
    spec = CommandSpec(name="export", options=[], min_args=0)
    result = parse_command(spec, "export --bad foo")
    assert not result.ok
    assert "Unknown option" in (result.error or "")


def test_parse_command_missing_required_option():
    spec = CommandSpec(
        name="backtest",
        options=[OptionSpec(name="strategy", short="s", required=True)],
    )
    result = parse_command(spec, "backtest")
    assert not result.ok
    assert "Missing required option" in (result.error or "")


def test_parse_command_arg_limits():
    spec = CommandSpec(name="view", options=[], min_args=1, max_args=2)
    result = parse_command(spec, "view")
    assert not result.ok
    assert "Missing required arguments" in (result.error or "")
    result = parse_command(spec, "view one two three")
    assert not result.ok
    assert "Too many arguments" in (result.error or "")


def test_parse_command_short_option():
    spec = CommandSpec(
        name="export",
        options=[OptionSpec(name="format", short="f", required=True)],
    )
    result = parse_command(spec, "export -f csv")
    assert result.ok
    assert result.options["format"] == "csv"
