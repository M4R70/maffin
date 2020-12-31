from discord.ext import commands
import utils.db as db
import discord
import random
import os
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev
import sys
import cloudpickle

from operator import itemgetter

from pympler import tracker

class DevOps(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@dev()
	@commands.command()
	async def git_pull(self, ctx):
		os.system("git pull")
		await ctx.send('Done')
	@dev()
	@commands.command()
	async def mem_check(self, ctx):
		mem = tracker.SummaryTracker()
		print(sorted(mem.create_summary(), reverse=True, key=itemgetter(2))[:10])

def setup(bot):
	bot.add_cog(DevOps(bot))
