from discord.ext import commands
import utils.db as db
import discord
import random
import os
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev
import sys
import pickle

def sizeof(obj):
    size = sys.getsizeof(obj)
    if isinstance(obj, dict): return size + sum(map(sizeof, obj.keys())) + sum(map(sizeof, obj.values()))
    if isinstance(obj, (list, tuple, set, frozenset)): return size + sum(map(sizeof, obj))
    return size

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
			size_estimate = len(pickle.dumps(cog))
			res += cog_name + " " + str(size_estimate) + '\n'
		await ctx.send(res)


def setup(bot):
	bot.add_cog(DevOps(bot))
