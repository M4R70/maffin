from discord.ext import commands
import discord


class staffPing(commands.Cog):
	def __init__(self,bot):
		self.bot = bot
		self.open_cases = []


	def validate_settings(self,settings,guild):
		try: 
			if settings["enabled"]:
				pingRole = [r for r in guild.roles if r.id == settings['role_id']]
				if len(pingRole) == 0:
					return "staffPing: role not found"
				pingChannel = guild.get_channel(settings["channel_id"])
				if pingChannel == None:
					return "staffPing: channel not found"
		
		except KeyError as e:
			return f"staffPing, Missing field {e}"
		
		return True
		

	@commands.Cog.listener()
	async def on_reaction_add(self,reaction,user):
		if user.bot:
			return
		if reaction.message.id in self.open_cases:
			await reaction.message.delete()
		
	

	@commands.Cog.listener()
	async def on_message(self,message):
		settings = await self.bot.cogs["Settings"].get(message.guild.id,"staffPing")
		if settings['enabled']:
			pingRole = [r for r in message.guild.roles if r.id == settings['role_id']][0]
			if pingRole in message.role_mentions:
				pingChannel = message.guild.get_channel(settings["channel_id"])
				content = message.clean_content.replace('@'+pingRole.name,'')
				if content == None or content == '':
					content = '[empty message]'
				e = discord.Embed()
				e.colour = discord.Colour.red()
				e.title = 'Ping Alert!'
				e.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
				e.add_field(name="Channel",value=message.channel.name,inline=False)
				e.add_field(name="Message",value=content,inline=False)
				e.add_field(name="Jump Link",value=f"[here]({message.jump_url})")
				case = await pingChannel.send('@here',embed=e)
				await message.channel.send("The Staff Team has been alerted :thumbsup:")
				await case.add_reaction("\U00002611")
				self.open_cases.append(case.id)

def setup(bot):
    bot.add_cog(staffPing(bot))