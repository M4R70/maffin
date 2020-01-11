from discord.ext import commands
import discord
import utils.db
from collections import defaultdict
from utils.checks import dev
from ruamel import yaml
from collections import defaultdict

class Settings(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		# self.default_settings = defaultdict(lambda :False) #store this on db, with a better default?
		disabled = defaultdict(lambda: {"enabled":False}  )
		self.default_settings = defaultdict(lambda : disabled)

	async def get(self, guild_id, cogName=None):
		d = await utils.db.findOne("settings", {"guild_id": guild_id})
		if d == None:
			return self.default_settings
		elif cogName == None:
			return d
		elif cogName in d:
			return d[cogName]
		else:
			return {"enabled":False}

	async def get_yaml(self, guild_id):
		d = await utils.db.findOne("settings_yaml", {"guild_id": guild_id})
		if d == None:
			return "None"
		return d["settings"]

	async def set(self, guild_id, new_settings):
		await utils.db.updateOne("settings", {"guild_id": guild_id}, {"$set": new_settings})

	def validate_settings(self, settings, guild):
		return True

	def validate(self, settings, guild):
		for cogName in self.bot.cogs:
			cog = self.bot.cogs[cogName]
			s = settings.get(cogName, {})
			print(cogName)
			validation = cog.validate_settings(s, guild)
			if validation != True:
				return validation
		return True

	@commands.command(aliases=["show_settings"])
	async def get_settings(self, ctx):
		d = await self.get_yaml(ctx.guild.id)
		await ctx.send(d)

	@commands.command()
	@dev()  # admin
	async def set_settings(self, ctx, *, new_settings: str):
		guild_id = ctx.guild.id
		new_settings_dict = yaml.safe_load(new_settings)
		validation = self.validate(new_settings_dict, ctx.guild)
		if validation == True:
			await utils.db.updateOne("settings_yaml", {"guild_id": guild_id}, {"$set": {"settings": new_settings}})
			await self.set(ctx.guild.id, new_settings_dict)
			await ctx.send("Settings updated :thumbsup:")
		else:
			await ctx.send(f"Error: {validation}")


def setup(bot):
	bot.add_cog(Settings(bot))
