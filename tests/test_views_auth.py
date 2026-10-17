from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER
from homeassistant.exceptions import Unauthorized

from custom_components.nanokvm_pro_desk_screen.views import (
    DeskScreenAgentLifecycleView,
    DeskScreenInputView,
    DeskScreenResourceView,
)

VIEWS = [
    (DeskScreenResourceView, "get"),
    (DeskScreenInputView, "post"),
    (DeskScreenAgentLifecycleView, "post"),
]


@pytest.mark.parametrize(("view_cls", "method"), VIEWS)
def test_views_reject_non_admin_users(view_cls: Any, method: str) -> None:
    assert view_cls.requires_auth is True
    view = view_cls()
    request = {KEY_HASS_USER: SimpleNamespace(is_admin=False)}

    with pytest.raises(Unauthorized):
        asyncio.run(getattr(view, method)(request, "entry", "anything"))


class _AdminRequest(dict):
    """Just enough of a request for the view decorators."""

    def __init__(self, body: object) -> None:
        super().__init__({KEY_HASS_USER: SimpleNamespace(is_admin=True)})
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_get_entry=lambda _id: None))
        self.app = {KEY_HASS: hass}
        self._body = body

    async def json(self) -> object:
        return self._body


@pytest.mark.parametrize(
    ("view_cls", "body", "status"),
    [
        (DeskScreenInputView, {"x": 1}, 404),  # valid body, unknown entry
        (DeskScreenAgentLifecycleView, {"ssh_password": "pw"}, 404),
        (DeskScreenAgentLifecycleView, {"ssh_port": 70000}, 400),
        (DeskScreenAgentLifecycleView, [1], 400),
    ],
)
def test_post_views_validate_the_body_then_look_up_the_entry(
    view_cls: type, body: object, status: int
) -> None:
    response = asyncio.run(view_cls().post(_AdminRequest(body), entry_id="entry", action="install"))

    assert response.status == status
