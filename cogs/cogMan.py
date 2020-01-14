from discord.ext import commands
from utils.checks import dev
import traceback
import importlib
import cogs
import os


def find_full_cog_name(cog):

	if cog + '.py' in os.listdir('cogs'):
		cog = 'cogs.' + cog
	elif cog + '.py' in os.listdir('cogs/dev'):
		cog = 'cogs.dev.' + cog
	elif cog + '.py' in os.listdir('cogs/feature'):
		cog = 'cogs.feature.' + cog
	elif cog + '.py' in os.listdir('cogs/meta'):
		cog = 'cogs.meta.' + cog
	else:
		cog = 'cogs.' + cog
	return cog


class cogMan(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.last = "cogs.cogMan"

	def validate_settings(self, settings, guild):
		return True

	@commands.command()
	@dev()
	async def print_cogs(self, ctx):
		m = ""
		for cog in self.bot.cogs:
			m += cog + '\n'
		await ctx.send(m)

	@commands.command()
	@dev()
	async def reload_all(self, ctx):
		for cog in os.listdir('cogs/'):
			cogname = cog[:-3]
			if cog.endswith('.py'):
				try:
					bot.reload_extension("cogs." + cogname)
				except:
					try:
						bot.load_extension("cogs." + cogname)
						await  self.do_on_load(cogname)
					except:
						print(f"error loading {cogname}")

	@commands.command(aliases=["r"])
	@dev()
	async def reload(self, ctx, *, cog=None):
		print(self.bot.cogs.keys())
		cogname = cog

		if cog == None:
			cog = self.last
			cogname = cog.split('.')[-1]

		cog = find_full_cog_name(cog)

		self.last = cogname

		try:
			if cog == "cogs.meta.heartbeat":  # make this an automatic thing (or as automatic as possible)
				self.bot.cogs["heartbeat"].kill_loop()
			self.bot.reload_extension(cog)
			if hasattr(self.bot.cogs[cogname],'on_reload'):
				await self.bot.cogs[cogname].on_reload()
			await ctx.send(f'{cog} Reloaded')
			print(f'-------------{cog} Reloaded--------------')
		except Exception as e:
			await ctx.send("""**Traceback:**\n```{0}```\n""".format(
				' '.join(traceback.format_exception(None, e, e.__traceback__))))

	@commands.command()
	@dev()
	async def unload(self, ctx, *, cog: str):
		self.last = cog
		try:
			cog = find_full_cog_name(cog)
			self.bot.unload_extension(cog)
			await ctx.send(f'{cog} Unloaded')
			print(f'-------------{cog} Unloaded--------------')
		except Exception as e:
			await ctx.send("""**Traceback:**\n```{0}```\n""".format(
				' '.join(traceback.format_exception(None, e, e.__traceback__))))

	@commands.command(aliases=["l"])
	@dev()
	async def load(self, ctx, *, cog=None):
		try:
			self._load_cog(cog)
			await ctx.send(f'{cog} Loaded')
		except Exception as e:
			await ctx.send("""**Traceback:**\n```{0}```\n""".format(
				' '.join(traceback.format_exception(None, e, e.__traceback__))))

	def _load_cog(self, cog):

		if cog == None:
			cog = self.last
		elif cog.endswith('.py'):
			cog = cog[:-3]

		cog = find_full_cog_name(cog)
		self.last = cog
		importlib.reload(cogs)
		self.bot.load_extension(cog)

		print(f'-------------{cog} Loaded--------------')


def setup(bot):
	bot.add_cog(cogMan(bot))
