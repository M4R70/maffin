from discord.ext import commands
import utils.db as db
import discord
import random
import os
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev
import sys
import cloudpickle

from types import ModuleType, FunctionType
from gc import get_referents

# Custom objects know their class.
# Function objects seem to know way too much, including modules.
# Exclude modules as well.
BLACKLIST = type, ModuleType, FunctionType


def getsize(obj):
    """sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
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
			res += cog_name + " " + str(getsize(cog)) + '\n'
		await ctx.send(res)


def setup(bot):
	bot.add_cog(DevOps(bot))
