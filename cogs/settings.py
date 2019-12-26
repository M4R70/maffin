from discord.ext import commands
import discord
import utils.db
from collections import defaultdict
from utils.checks import dev
from ruamel import yaml
import ruamel 




class Settings(commands.Cog):
	def __init__(self,bot):
		self.bot = bot
		#self.default_settings = defaultdict(lambda :False) #store this on db, with a better default?
		self.default_settings = {"staffPing":{"enabled":False}}
	
	
	async def get(self,guild_id,cogName=None):
		d = await utils.db.findOne("settings",{"guild_id":guild_id})
		if d == None:
			return self.default_settings
		if cogName == None:
			return d
		else:
			return d[cogName]
	
	async def set(self,guild_id,new_settings):
		await utils.db.updateOne("settings",{"guild_id":guild_id},{"$set":new_settings})

	def validate_settings(self,settings,guild):		
		return True

	def validate(self,settings,guild):
		for cogName in self.bot.cogs:
			cog = self.bot.cogs[cogName]
			s = settings.get(cogName,{})
			print(cogName)
			validation = cog.validate_settings(s,guild)
			if validation != True:
				return validation
		return True
			

	@commands.command()
	async def get_settings(self,ctx,*,cogName=None):
		d = await self.get(ctx.guild.id,cogName)
		txt = str(yaml.dump(d))
		split = txt.split(' ')
		for coso in split:
			if coso.startswith('!!python/object/new'):
				split.remove(coso)
		await ctx.send(''.join(split))

	@commands.command()
	@dev() #admin
	async def set_settings(self,ctx,*,new_settings:str):
		new_settings = yaml.load(new_settings)
		validation = self.validate(new_settings,ctx.guild)
		if validation == True:
			await self.set(ctx.guild.id,new_settings)
			await ctx.send("Settings updated :thumbsup:")
		else:
			await ctx.send(f"Error: {validation}")



def setup(bot):
    bot.add_cog(Settings(bot))