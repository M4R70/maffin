from discord.ext import commands
import utils.db as db
import discord
import random
import os
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev


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
		res = ":) \n"
		for cog_name,cog in self.bot.cogs.items():
			res += cog_name + " " + sys.getsizeof(cog) + '\n'
		await ctx.send(res)

def setup(bot):
	bot.add_cog(DevOps(bot))
