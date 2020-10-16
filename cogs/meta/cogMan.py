from discord.ext import commands
from utils.checks import dev
from utils.exceptions import report_meta
import utils.db
import utils.checks
import importlib
import logging
import os


#
# def get_cog_topography(topography):
# 	if topography == {}:
# 		folders = [f for f in os.listdir('./cogs') if os.path.isdir('./cogs/'+f)]
# 		return {f:{} for f in folders}
# 	for f,x in topography.items():
# 		if os.path.isdir('./cogs/'+f):


def get_cog_topography():
	res = {}

	for folder in os.listdir('./cogs'):
		if os.path.isdir('./cogs/' + folder):
			for filename in os.listdir(f'./cogs/{folder}/'):
				if filename.endswith('.py'):
					filename = filename.replace('.py', '')
					res[filename] = folder
	return res


class cogMan(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.last = "cogMan"
		self.topography = get_cog_topography()

	def get_full_cog_name(self, cogName):
		cogFolder = self.topography[cogName]
		return f'cogs.{cogFolder}.{cogName}'

	@commands.command(aliases=["l"])
	@dev()
	async def load_cog(self, ctx,cogName=None):
		await self._load_cog(ctx=ctx, cogName=cogName)

	async def _load_cog(self, ctx=None, cogName=None):
		if cogName is None:
			cogName = self.last
		self.topography = get_cog_topography()
		full_cog_name = self.get_full_cog_name(cogName)
		self.last = cogName
		try:
			print(full_cog_name)
			#importlib.reload(full_cog_name)
			self.bot.load_extension(full_cog_name)
			ok_msg = f"loaded {full_cog_name}"
			logging.info(ok_msg)
			if ctx is not None:
				await ctx.send(ok_msg)
			return True
		except Exception as e:
			error_msg = f"ERROR loading {full_cog_name}"
			await report_meta(e, error_msg=error_msg)
			return False

	@commands.command()
	@dev()
	async def unload_cog(self, ctx,cogName=None):
		if cogName is None:
			cogName = self.last
		full_cog_name = self.get_full_cog_name(cogName)
		self.bot.unload_extension(full_cog_name)
		logging.info(f"unloaded {full_cog_name}")
		ok_msg = f"unloaded {full_cog_name}"
		logging.info(ok_msg)
		await ctx.send(ok_msg)

	@commands.command(aliases=["r"])
	@dev()
	async def reload_cog(self, ctx, *, cogName=None):
		if cogName is None:
			cogName = self.last
		print(cogName)
		importlib.reload(utils.db)
		importlib.reload(utils.checks)
		await ctx.invoke(self.unload_cog, cogName)
		await ctx.invoke(self.load_cog, cogName)

	async def load_all_cogs(self):
		self.topography = get_cog_topography()
		for cogName in self.topography.keys():
			if cogName != "cogMan":
				ok = await self._load_cog(cogName=cogName)
				if not ok:
					logging.warning(f"ERROR LOADING {cogName}")


def setup(bot):
	bot.add_cog(cogMan(bot))
