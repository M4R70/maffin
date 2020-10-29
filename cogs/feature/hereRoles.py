from collections import defaultdict
from discord.ext import commands
import discord
from utils import db
from utils.checks import is_cog_enabled
import datetime
import timedelta


class HereRoles(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.open_cases = defaultdict(lambda: [])

	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if user.bot:
			return
		guild = reaction.message.guild
		open_cases_list = [x[0] for x in self.open_cases[guild.id]]
		if reaction.message in open_cases_list:
			index = open_cases_list.index(reaction.message)
			case_channel = self.open_cases[guild.id][index][1].channel
			for i in range(index, -1, -1):
				case = self.open_cases[guild.id][i]
				if case[1].channel == case_channel:
					await self.remove_case(case)


	async def remove_case(self, case):
		self.open_cases[case[0].guild.id].remove(case)
		await case[0].delete()

	def should_ping(self,message):
		for case in reversed(self.open_cases[message.guild.id]):
			if case[1].channel == message.channel:
				if message.created_at - case[1].created_at < datetime.timedelta(minutes=3):
					return False
		return True

	@commands.Cog.listener()
	async def on_message(self, message):
		enabled = await is_cog_enabled(None, message.guild.id, 'hereRoles')
		if not enabled:
			return
		mentioned_ids = [r.id for r in message.role_mentions]
		if not mentioned_ids:
			return
		settings = await db.get_setting(message.guild.id, 'hereRoles')
		for r_id in mentioned_ids:
			if str(r_id) in settings:
				ping_channel = message.guild.get_channel(settings[str(r_id)])
				ping_role = message.guild.get_role(r_id)
				content = message.clean_content.replace('@' + ping_role.name, '')
				if content is None or content == '':
					content = '[empty message]'
				e = discord.Embed()
				e.colour = discord.Colour.red()
				e.title = 'Ping Alert!'
				e.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
				e.add_field(name="Channel", value=message.channel.name, inline=False)
				e.add_field(name="Message", value=content, inline=False)
				e.add_field(name="Jump Link", value=f"[here]({message.jump_url})")
				should_ping = self.should_ping(message)
				if should_ping:
					case = await ping_channel.send('@here', embed=e)
				else:
					if content == '[empty message]':
						return
					else:
						case = await ping_channel.send( embed=e)
				await message.channel.send("Notification sent :thumbsup:")
				await case.add_reaction("\U00002611")
				self.open_cases[message.guild.id].append([case, message])

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(HereRoles(bot))
