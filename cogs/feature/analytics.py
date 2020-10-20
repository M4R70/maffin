from collections import defaultdict
from discord.ext import commands
import discord
from utils import db
from utils.checks import is_cog_enabled
import pandas as pd

def voice_state_diff(before, after):
	if before.channel != after.channel:
		if before.channel is None or before.afk and after.channel is not None:
			return f"connected"
		elif after.channel is None and before.channel is not None:
			return f"disconnected"
		elif before.channel is not None and after.channel is not None:
			return f"moved"
	else:
		return None


class Analytics(commands.Cog):
	def __init__(self, bot):
		self.bot = bot


	@commands.command()
	async def insights(self,ctx,member:discord.Member):
		text_data = await db.get(ctx.guild.id,'analytics.text',{},list=True)
		df = pd.DataFrame(text_data)
		print(len(text_data))
		df.to_csv('df.csv')



	@commands.Cog.listener()
	async def on_message(self, message):
		enabled = await is_cog_enabled(None, message.guild.id, 'analytics')
		if enabled:
			doc = {'message_id': message.id, 'channel_id': message.channel.id, 'len': len(message.content),
				   'author_id': message.author.id}
			await db.insert(message.guild.id, 'analytics.text', doc)

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):

		enabled = await is_cog_enabled(None, member.guild.id, 'analytics')
		if not enabled:
			return

		diff = voice_state_diff(before, after)
		if diff is None:
			return

		doc = {'member_id': member.id, 'event': diff}
		if diff == "connected":
			doc['channel_id'] = after.channel.id
		elif diff == "disconnected":
			doc['channel_id'] = before.channel.id
		elif diff == "moved":
			doc['before_channel_id'] = before.channel.id
			doc['after_channel_id'] = after.channel.id
		await db.insert(member.guild.id,'analytics.voice',doc)

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(Analytics(bot))
