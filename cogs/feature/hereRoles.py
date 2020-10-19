from collections import defaultdict
from discord.ext import commands
import discord
from utils import db
from utils.checks import is_cog_enabled


class HereRoles(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.open_cases = defaultdict(lambda: [])

	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if user.bot:
			return
		if reaction.message.id in self.open_cases[reaction.message.guild.id]:
			await reaction.message.delete()

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
				case = await ping_channel.send('@here', embed=e)
				await message.channel.send("Notification sent :thumbsup:")
				await case.add_reaction("\U00002611")
				self.open_cases[message.guild.id].append(case.id)

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(HereRoles(bot))
