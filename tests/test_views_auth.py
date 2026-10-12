from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from homeassistant.components.http import KEY_HASS_USER
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
def test_views_reject_non_admin_users(view_cls: type, method: str) -> None:
    assert view_cls.requires_auth is True
    view = view_cls(SimpleNamespace(data={}), "coordinators")
    request = {KEY_HASS_USER: SimpleNamespace(is_admin=False)}

    with pytest.raises(Unauthorized):
        asyncio.run(getattr(view, method)(request, "entry", "anything"))
