"""Profile selection widget."""

from __future__ import annotations

from textual.widgets import OptionList
from textual.widgets.option_list import Option
from textual.message import Message

from ..state.profiles import list_profiles


class ProfileSelected(Message):
    def __init__(self, profile_name: str) -> None:
        super().__init__()
        self.profile_name = profile_name


class ProfileSelector(OptionList):
    def __init__(self, active_profile: str) -> None:
        profiles = list_profiles()
        options = [Option(p.label, id=p.name) for p in profiles]
        super().__init__(*options)
        self.highlighted = 0
        for idx, option in enumerate(options):
            if option.id == active_profile:
                self.highlighted = idx
                break

    def on_mount(self) -> None:
        self.index = self.highlighted

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.post_message(ProfileSelected(str(event.option.id)))
