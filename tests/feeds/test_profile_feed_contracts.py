from tui.feeds.contracts import PROFILE_ENDPOINT_CONTRACTS
from tui.feeds.url_builder import ENDPOINT_SPECS


def test_profile_feed_contract_endpoints_exist_in_allowlist():
    missing: list[str] = []
    for profile_contract in PROFILE_ENDPOINT_CONTRACTS.values():
        for endpoints in profile_contract.values():
            for endpoint_key in endpoints:
                if endpoint_key not in ENDPOINT_SPECS:
                    missing.append(endpoint_key)
    assert not missing, f"Missing endpoint specs: {sorted(set(missing))}"


def test_profile_feed_contracts_are_not_empty():
    assert PROFILE_ENDPOINT_CONTRACTS
    for profile, panels in PROFILE_ENDPOINT_CONTRACTS.items():
        assert panels, f"{profile} has no panel contracts"
