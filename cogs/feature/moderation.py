# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import utils.db
import datetime
import utils.db as db


class Moderation(commands.Cog):
	"""The description for Moderation goes here."""

	def __init__(self, bot):
		self.bot = bot
		self.mod_register = {"ban": {}, 'kick': {}}

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		if member.voice.mute:
			await db.update_setting(member.guild.id, 'to_be_server_muted', {"$set": {str(member.id): True}})
		return

	@commands.has_guild_permissions(ban_members=True)
	@commands.command()
	async def ban(self, ctx, member: discord.Member, reason=None):
		"""bans a member"""
		self.mod_register['ban'][member.id] = ctx.author
		await member.ban(reason=reason)

	@commands.has_guild_permissions(kick_members=True)
	@commands.command()
	async def kick(self, ctx, member: discord.Member, reason=None):
		"""kicks a member"""
		# self.mod_register['kick'][member.id] = ctx.author
		await member.ban(reason=reason)

	@commands.has_guild_permissions(mute_members=True)
	@commands.command()
	async def mute(self, ctx, member: discord.Member):
		"""server mute a member"""

		if member.voice is not None:
			await member.edit(mute=True)
			await ctx.send(f"{member} was muted :thumbsup:")
		else:
			await db.update_setting(member.guild.id, 'to_be_server_muted', {"$set": {str(member.id): True}})
			await ctx.send(f'{member} will be muted :thumbsup:')
		return

	@commands.has_guild_permissions(mute_members=True)
	@commands.command()
	async def unmute(self, ctx, member: discord.Member):
		"""server unmute a member"""

		if member.voice is not None:
			await member.edit(mute=False)
			await  ctx.send(f"{member} was unmuted :thumbsup:")
		else:
			await db.update_setting(member.guild.id, 'to_be_server_muted', {"$set": {str(member.id): False}})
			await ctx.send(f"{member} will be unmuted :thumbsup:")
		return

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		if before.channel != after.channel:
			if before.channel is None or before.afk and after.channel is not None:
				db_info = await db.get_setting(member.guild.id, 'to_be_server_muted')
				should_mute = db_info.get(str(member.id))
				if should_mute is not None:
					if should_mute:
						await member.edit(mute=True)
					elif not should_mute:
						await member.edit(mute=False)

					await db.update_setting(member.guild.id, 'to_be_server_muted', {"$unset": {str(member.id): 1}})

	@commands.guild_only()
	@commands.command()
	@commands.has_permissions(manage_messages=True)
	async def clear(self, ctx, *args):
		"""clears a text channel"""
		limit = None
		guy = None
		message = None
		check = None
		before = None
		after = None
		member_converter = discord.ext.commands.MemberConverter()
		message_converter = discord.ext.commands.MessageConverter()

		for arg in args:
			if guy is None:
				try:
					guy = await member_converter.convert(ctx, arg)
				except discord.ext.commands.errors.BadArgument:
					pass
				if guy is not None:
					continue
			if message is None:
				try:
					message = await message_converter.convert(ctx, arg)
				except discord.ext.commands.errors.BadArgument:
					pass
				if message is not None:
					continue
			if limit is None:
				limit = min(int(arg) + 1, 100)

		if limit is None:
			limit = 50

		if guy is not None:
			def check(message):
				return message.author == guy

		if message is not None:
			after = message.created_at
			limit = 300

		await ctx.channel.purge(limit=limit, check=check, after=after)
		msg = await ctx.channel.send("**Cleared** :thumbsup:")
		await msg.delete(delay=1)


def setup(bot):
	bot.add_cog(Moderation(bot))
