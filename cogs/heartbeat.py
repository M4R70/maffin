# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import utils.db
import datetime
import timedelta
import asyncio


class heartbeat(commands.Cog):
    """The description for Heartbeat goes here."""

    def validate_settings(self, settings, guild):
        return True

    def __init__(self, bot):
        self.bot = bot
        self.loop = self.bot.loop.create_task(self.loop())
        self.errorCog = self.bot.cogs["errorHandling"]
        self.dead = False

    def kill_loop(self):
        self.dead = True

    async def loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed() and not self.dead:
            hb = await utils.db.findOne("heartbeat", {})
            now = datetime.datetime.now()
            try:
                last_hb = hb["datetime"]
            except TypeError:
                await log_heartbeat(now)
                return

            if last_hb < (now - timedelta.Timedelta(minutes=3)):  # hay downtime
                await self.log_downtime(last_hb, now)

            else:  # todo piola
                await log_heartbeat(now)

            await asyncio.sleep(60 * 2)

        print("hb loop down")

    async def log_downtime(self, last_hb, now):
        downtime_log = {
            "from": last_hb,
            "to": now
        }
        new_hb = {
            "datetime": now,
        }
        await self.errorCog.dev_report("heartbeat", f"Downtime from {to_str(last_hb)} to {to_str(now)}")
        await utils.db.insertOne("downtime", downtime_log)
        await utils.db.clear("heartbeat")
        await utils.db.insertOne("heartbeat", new_hb)


async def log_heartbeat(now):
    new_hb = {
        "datetime": now,
    }
    await utils.db.clear("heartbeat")
    await utils.db.insertOne("heartbeat", new_hb)


def to_str(dt):
    return dt.strftime("%m/%d/%Y, %H:%M:%S")


def setup(bot):
    bot.add_cog(heartbeat(bot))
