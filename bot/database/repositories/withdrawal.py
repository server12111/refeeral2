from datetime import datetime, date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Withdrawal
from bot.database.repositories.base import BaseRepository


class WithdrawalRepository(BaseRepository):
    async def create(self, user_id: int, amount: float) -> Withdrawal:
        w = Withdrawal(user_id=user_id, amount=amount)
        self.session.add(w)
        await self.session.flush()
        return w

    async def get(self, withdrawal_id: int) -> Withdrawal | None:
        return await self.session.get(Withdrawal, withdrawal_id)

    async def pending_count(self) -> int:
        result = await self.session.execute(
            select(func.count(Withdrawal.id)).where(Withdrawal.status == "pending")
        )
        return result.scalar() or 0

    async def approved_sum(self) -> float:
        result = await self.session.execute(
            select(func.sum(Withdrawal.amount)).where(Withdrawal.status == "approved")
        )
        return float(result.scalar() or 0)

    async def rejected_count(self) -> int:
        result = await self.session.execute(
            select(func.count(Withdrawal.id)).where(Withdrawal.status == "rejected")
        )
        return result.scalar() or 0

    async def approve(self, withdrawal_id: int) -> Withdrawal | None:
        w = await self.session.get(Withdrawal, withdrawal_id)
        if w and w.status == "pending":
            w.status = "approved"
            w.processed_at = datetime.utcnow()
            await self.session.commit()
        return w

    async def reject(self, withdrawal_id: int) -> Withdrawal | None:
        w = await self.session.get(Withdrawal, withdrawal_id)
        if w and w.status == "pending":
            w.status = "rejected"
            w.processed_at = datetime.utcnow()
            await self.session.commit()
        return w
