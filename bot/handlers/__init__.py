from aiogram import Router

from bot.handlers import (
    start, earn, withdraw, bonus, tasks,
    profile, top, games, duel, cases, wheel, lottery,
    casino, mines, tower, auction,
)
from bot.handlers.admin import router as admin_router

router = Router()

router.include_router(start.router)
router.include_router(earn.router)
router.include_router(withdraw.router)
router.include_router(bonus.router)
router.include_router(tasks.router)
router.include_router(profile.router)
router.include_router(top.router)
router.include_router(games.router)
router.include_router(casino.router)
router.include_router(duel.router)
router.include_router(cases.router)
router.include_router(wheel.router)
router.include_router(lottery.router)
router.include_router(mines.router)
router.include_router(tower.router)
router.include_router(auction.router)
router.include_router(admin_router)
