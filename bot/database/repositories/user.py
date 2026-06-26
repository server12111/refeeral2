from datetime import datetime, date

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_or_create(
        self,
        user_id: int,
        username: str | None,
        first_name: str,
        referrer_id: int | None = None,
    ) -> tuple[User, bool]:
        user = await self.session.get(User, user_id)
        if user:
            user.username = username
            user.first_name = first_name
            user.last_seen_at = datetime.utcnow()
            await self.session.commit()
            return user, False
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            referrer_id=referrer_id,
        )
        self.session.add(user)
        await self.session.commit()
        return user, True

    async def total_count(self) -> int:
        result = await self.session.execute(select(func.count(User.user_id)))
        return result.scalar() or 0

    async def today_count(self) -> int:
        today = datetime.combine(date.today(), datetime.min.time())
        result = await self.session.execute(
            select(func.count(User.user_id)).where(User.created_at >= today)
        )
        return result.scalar() or 0

    async def total_balance(self) -> float:
        result = await self.session.execute(select(func.sum(User.stars_balance)))
        return float(result.scalar() or 0)

    async def top_by_referrals(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(desc(User.referrals_count)).limit(limit)
        )
        return list(result.scalars().all())

    async def top_by_balance(self, limit: int = 10) -> list[User]:
        result = await self.session.execute(
            select(User).order_by(desc(User.stars_balance)).limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_username(self, username: str) -> User | None:
        uname = username.lstrip("@")
        result = await self.session.execute(
            select(User).where(User.username == uname)
        )
        return result.scalar_one_or_none()

    async def all_active_ids(self) -> list[int]:
        result = await self.session.execute(
            select(User.user_id).where(User.is_blocked == False)
        )
        return list(result.scalars().all())
