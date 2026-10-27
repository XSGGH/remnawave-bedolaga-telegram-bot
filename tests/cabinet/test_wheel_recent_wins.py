"""Публичная лента выигрышей колеса: анонимна и ограничена."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.cabinet.routes import wheel as wheel_routes
from app.cabinet.schemas.wheel import RecentWinItem


def _spin(spin_id: int, name: str, with_prize: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=spin_id,
        user_id=1000 + spin_id,
        prize_type='subscription_days',
        prize_display_name=name,
        prize=SimpleNamespace(emoji='📅') if with_prize else None,
        created_at=datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
    )


def test_recent_win_item_has_no_user_fields() -> None:
    assert set(RecentWinItem.model_fields) == {'id', 'prize_type', 'prize_display_name', 'emoji', 'created_at'}


@pytest.mark.asyncio
async def test_recent_wins_is_anonymous_and_cached() -> None:
    wheel_routes._recent_wins_cache.clear()
    spins = [_spin(2, '7 дней'), _spin(1, '3 дня', with_prize=False)]
    crud = AsyncMock(return_value=spins)
    with patch.object(wheel_routes, 'get_recent_public_wins', crud):
        first = await wheel_routes.get_recent_wins(limit=20, user=SimpleNamespace(id=1), db=AsyncMock())
        second = await wheel_routes.get_recent_wins(limit=20, user=SimpleNamespace(id=2), db=AsyncMock())

    assert [item.prize_display_name for item in first.items] == ['7 дней', '3 дня']
    assert first.items[1].emoji == '🎁'
    assert 'user_id' not in first.items[0].model_dump()
    assert second is first
    crud.assert_awaited_once()


@pytest.mark.asyncio
async def test_recent_wins_clamps_limit() -> None:
    wheel_routes._recent_wins_cache.clear()
    crud = AsyncMock(return_value=[])
    with patch.object(wheel_routes, 'get_recent_public_wins', crud):
        await wheel_routes.get_recent_wins(limit=9999, user=SimpleNamespace(id=1), db=AsyncMock())
    assert crud.await_args.kwargs['limit'] == 50
