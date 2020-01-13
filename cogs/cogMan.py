from discord.ext import commands
from utils.checks import dev
import traceback
import importlib
import cogs


class cogMan(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.last = "cogs.cogManager"

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
					await self.do_on_load(cogname)
				except:
					try:
						bot.load_extension("cogs." + cogname)
						await  self.do_on_load(cogname)
					except:
						print(f"error loading {cogname}")

	@commands.command(aliases=["r"])
	@dev()
	async def reload(self, ctx, *, cog=None):

		if cog == None:
			cog = self.last
		else:
			cog = 'cogs.' + cog
		self.last = cog
		try:
			if cog == "cogs.heartbeat":  # make this an automatic thing (or as automatic as possible)
				self.bot.cogs["heartbeat"].kill_loop()
			self.bot.reload_extension(cog)
			await  self.do_on_load(cog[5:])
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
			cog = 'cogs.' + cog
			self.bot.unload_extension(cog)
			await ctx.send(f'{cog} Unloaded')
			print(f'-------------{cog} Unloaded--------------')
		except Exception as e:
			await ctx.send("""**Traceback:**\n```{0}```\n""".format(
				' '.join(traceback.format_exception(None, e, e.__traceback__))))

	@commands.command(aliases=["l"])
	@dev()
	async def load(self, ctx, *, cog=None):

		if cog == None:
			cog = self.last
		else:
			cog = 'cogs.' + cog
		self.last = cog

		try:
			importlib.reload(cogs)
			self.bot.load_extension(cog)
			await  self.do_on_load(cog[5:])
			await ctx.send(f'{cog} Loaded')
			print(f'-------------{cog} Loaded--------------')
		except Exception as e:
			await ctx.send("""**Traceback:**\n```{0}```\n""".format(
				' '.join(traceback.format_exception(None, e, e.__traceback__))))

	async def do_on_load(self, cogName):
		cog = self.bot.cogs[cogName]
		if hasattr(cog, 'on_load'):
			await cog.on_load()


def setup(bot):
	bot.add_cog(cogMan(bot))
