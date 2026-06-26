from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import PromoCode, PromoUse
from bot.database.repositories.base import BaseRepository


class PromoRepository(BaseRepository):
    async def get_by_code(self, code: str) -> PromoCode | None:
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.code == code.upper())
        )
        return result.scalar_one_or_none()

    async def already_used(self, code_id: int, user_id: int) -> bool:
        result = await self.session.execute(
            select(PromoUse.id).where(
                PromoUse.code_id == code_id,
                PromoUse.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def use(self, promo: PromoCode, user_id: int) -> bool:
        if not promo.is_active:
            return False
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            return False
        if promo.usage_limit > 0 and promo.used_count >= promo.usage_limit:
            return False
        if await self.already_used(promo.id, user_id):
            return False
        promo.used_count += 1
        self.session.add(PromoUse(code_id=promo.id, user_id=user_id))
        await self.session.commit()
        return True

    async def create(
        self,
        code: str,
        reward: float,
        usage_limit: int = 0,
        expires_at: datetime | None = None,
    ) -> PromoCode:
        p = PromoCode(
            code=code.upper(),
            reward_amount=reward,
            usage_limit=usage_limit,
            expires_at=expires_at,
        )
        self.session.add(p)
        await self.session.commit()
        return p

    async def all_active(self) -> list[PromoCode]:
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.is_active == True).order_by(PromoCode.id.desc())
        )
        return list(result.scalars().all())

    async def delete(self, promo_id: int) -> bool:
        p = await self.session.get(PromoCode, promo_id)
        if p:
            await self.session.delete(p)
            await self.session.commit()
            return True
        return False
