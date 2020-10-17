from discord.ext import commands, tasks
import utils.db as db
import discord
from utils.checks import is_cog_enabled, dev
import logging
from collections import defaultdict
import timeago
import datetime


async def get_channel(guild, channel_name):
	log_settings = await db.get_setting(guild.id, "logging")
	channel_id = log_settings.get(channel_name)
	channel = guild.get_channel(channel_id)
	if channel_id is not None and channel is None:
		logging.warning(f"can't get channel {channel_id} in {before.guild}")
	return channel


def member_embed(member, title="Insert a title you lazy dev!", color=discord.Colour.blue(), entry=None):
	e = discord.Embed()
	e.colour = color
	e.title = title
	e.set_author(name=member.display_name, icon_url=member.avatar_url)
	e.add_field(name="Account name", value=member.name, inline=True)
	e.add_field(name="User id", value=member.id, inline=True)
	if entry is not None:
		try:
			e.add_field(name="Moderator", value=f"{entry.user}", inline=False)
		except:
			e.add_field(name="Moderator", value="failed to obtain")

	return e


async def search_entry(guild, target_user, action):
	t = 1
	entry = None
	while entry == None:
		async for e in guild.audit_logs(action=action, limit=10):
			if e.target.id == target_user.id:
				return e
		await asyncio.sleep(t)
		t += t
		if t > 200:
			return "fail"


async def ask_for_reason(entry, message, user):
	mod = entry.user
	if mod is not None:
		await mod.send(
			f"Hey, you banned {str(user)} from {str(message.guild)} but you specified no reason. \n\nTo add one,"
			f" send me the command `!add_reason {message.id} <reason> ` "
			f"\n\nNote that you must send this command in the guild, and not here in DMs")


def voice_state_diff(before, after):
	if before.channel != after.channel:
		if before.channel == None or before.afk and after.channel != None:
			return f"connected to {after.channel.name}"
		elif after.channel == None and before.channel != None:
			return f"disconnected from {before.channel}"
		elif before.channel != None and after.channel != None:
			return f"moved from {before.channel.name} to {after.channel.name}"

	elif before.mute and not after.mute:
		return "Unmuted"
	elif not before.mute and after.mute:
		return "Muted"

	else:
		return None


async def log_server_mute(diff, member):
	channel = await get_channel(member.guild, 'mute_log_channel_id')
	if channel is None:
		return

	entry = await search_entry(member.guild, member, discord.AuditLogAction.member_update)

	if diff == "Muted":
		color = discord.Colour.red()
	else:
		color = discord.Colour.green()

	e = member_embed(member, title=f"{diff}", color=color, entry=entry)

	await channel.send(embed=e)


async def is_role_important(role):
	config = await db.get_setting(role.guild.id, 'logging')
	uninportant = config.get('unimportant', [])
	important = config.get('important', [])
	if role.id in uninportant:
		return False
	elif role.id in important:
		return True

	role_perms = set([str(x) for x, y in role.permissions if y])

	important_perms = {'kick_members', 'ban_members', 'administrator', 'administrator', 'manage_guild',
					   'manage_messages', 'mention_everyone', 'mute_members', 'deafen_members', 'move_members',
					   'manage_nicknames', 'manage_roles', 'manage_webhooks', 'manage_emojis'}

	important_perms_possesed = role_perms.intersection(important_perms)

	if important_perms_possesed:
		print(important_perms_possesed)
		return True
	else:
		return False


class Logging(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.invite_cache = defaultdict(lambda: {})
		self.crawl_invites.start()

	@commands.Cog.listener()
	async def on_member_join(self, member):
		channel = await get_channel(member.guild, 'join_log_channel_id')
		if channel is None:
			return

		possible_invites = await self.find_possible_invites(member.guild)
		nothing = "** **"

		e = discord.Embed()
		e.colour = discord.Colour.teal()
		e.title = f"{member}"
		e.set_author(name="Member Joined", icon_url=member.avatar_url)
		e.add_field(name="ID:", value=member.id)

		if len(possible_invites) == 1:
			e.add_field(name="Acount created", value=timeago.format(member.created_at, datetime.datetime.now()))
			e.add_field(name="Invite used", value=possible_invites[0].url, inline=False)
			e.add_field(name="Invite created by", value=str(possible_invites[0].inviter), inline=True)
			e.add_field(name="Number of uses", value=str(possible_invites[0].uses), inline=True)

		elif len(possible_invites) > 1:
			e.add_field(name="Possible invites used:", value=nothing, inline=False)
			for i in possible_invites:
				e.add_field(name=nothing, value=i.url, inline=False)
		else:
			e.add_field(name="Invite could not be retrieved", value=nothing, inline=False)

		try:
			await channel.send(embed=e)
		except discord.Forbidden:
			logging.waring(f"logging can't send channel on server {channel.guild} channel {channel} ")

	@commands.Cog.listener()
	async def on_message_edit(self, before, after):
		channel = await get_channel(before.guild, 'text_log_channel_id')
		if channel is None:
			return

		e = member_embed(after.author, color=discord.Colour.gold(), title="Message Edited")

		post_separate = False
		if len(before.content) < 1000 and len(after.content) < 1000:
			e.add_field(name="Before", value=f"{before.content}", inline=False)
			e.add_field(name="After", value=f"{after.content}", inline=False)
		else:
			e.add_field(name="Messages too long, will be posted below", value="** **", inline=False)
			post_separate = True

		e.add_field(name="Jump Link", value=f"[here]({after.jump_url})")

		try:

			await channel.send(embed=e)

			if post_separate:
				await channel.send("Before:")
				await channel.send(f"```{before.content}```")
				await channel.send("After:")
				await channel.send(f"```{after.content}```")

		except discord.Forbidden:
			await logging.warning("logs", f"Missing permission to post in {channel.name}")
		except discord.errors.HTTPException:
			pass

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		channel = await get_channel(member.guild, 'join_log_channel_id')
		if channel is None:
			return

		e = discord.Embed()
		e.colour = discord.Colour.dark_grey()
		e.title = f"{member}"
		e.set_author(name="Member Left", icon_url=member.avatar_url)
		e.add_field(name="ID:", value=member.id)

		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_unban(self, guild, user):
		channel = await get_channel(guild, 'ban_log_channel_id')
		if channel is None:
			return

		entry = await search_entry(guild, user, discord.AuditLogAction.unban)
		e = member_embed(user, title="UNBAN", color=discord.Colour.green(), entry=entry)

		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_ban(self, guild, user):
		channel = await get_channel(guild, 'ban_log_channel_id')
		if channel is None:
			return

		entry = await search_entry(guild, user, discord.AuditLogAction.ban)
		e = member_embed(user, title="BAN", color=discord.Colour.red(), entry=entry)

		e.add_field(name="Reason", value=entry.reason)

		message = await channel.send(embed=e)
		if entry.reason is None:
			await ask_for_reason(entry, message, user)

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		channel = await get_channel(message.guild, 'text_log_channel_id')
		if channel is None:
			return
		entry = await search_entry(message.guild, message.author, discord.AuditLogAction.message_delete)
		e = member_embed(message.author, color=discord.Colour.red(), title="Message Deleted", entry=entry)

		post_separate = False
		if len(message.content) < 1000:
			e.add_field(name="Message", value=f"{message.content}", inline=False)
		else:
			e.add_field(name="Message", value=f"Message too long, will be posted below this", inline=False)
			post_separate = True

		await channel.send(embed=e)
		if post_separate:
			await channel.send(f"```{message.content}```")

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		channel = await get_channel(member.guild, 'voice_log_channel_id')
		if channel is None:
			return

		diff = voice_state_diff(before, after)

		if diff is None:
			return

		elif diff == "Muted" or diff == "Unmuted":
			await log_server_mute(diff, member)
			return
		else:
			e = member_embed(member)
			e.title = diff

		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_update(self, before, after):

		e = member_embed(after, color=discord.Colour.purple())
		if before.roles != after.roles:
			channel = await get_channel(before.guild, 'role_log_channel_id')
			if channel is None:
				return
			before_roles = set(before.roles)
			after_roles = set(after.roles)
			role = before_roles.symmetric_difference(after_roles)
			role = role.pop()
			important = await is_role_important(role)

			if important:
				if role not in before_roles:
					e.title = "Role Added"
					e.add_field(name="Added role", value=f"{role}", inline=False)
				else:
					e.title = "Role Removed"
					e.add_field(name="Removed role", value=f"{role}", inline=False)
				await channel.send(embed=e)

	# if before.display_name != after.display_name:
	# 	channel = await get_channel(before.guild, 'member_log_channel_id')
	# 	if channel is None:
	# 		return
	# 	e.title = "Nickname Change"
	# 	e.add_field(name="Old", value=f"{before.display_name}", inline=False)
	# 	e.add_field(name="new", value=f"{after.display_name}", inline=False)
	# 	await channel.send(embed=e)
	#
	# elif before.name != after.name: #does not work?
	# 	channel = await get_channel(before.guild, 'member_log_channel_id')
	# 	if channel is None:
	# 		return
	# 	e.title = "Account Name Change"
	# 	e.add_field(name="Old", value=f"{before.display_name}", inline=False)
	# 	e.add_field(name="new", value=f"{after.display_name}", inline=False)
	# 	await channel.send(embed=e)

	@commands.has_permissions(ban_members=True)
	@commands.guild_only()
	@commands.command()
	async def add_reason(self, ctx, message_id: int, *, reason: str):
		channel = await get_channel(ctx.guild, 'ban_log_channel_id')
		if channel is None:
			return
		message = await channel.fetch_message(message_id)
		e = message.embeds[0]
		e.set_field_at(-1, name="Reason", value=reason, inline=False)
		await message.edit(embed=e)
		await ctx.send("Reason updated!")

	@tasks.loop(minutes=0, count=1)
	async def crawl_invites(self):
		await self.bot.wait_until_ready()
		for g in self.bot.guilds:
			is_enabled = await is_cog_enabled(None, guild_id=g.id, cogName='logging')
			if is_enabled:
				settings = await db.get_setting(g.id, 'logging')
				join_log_channel = settings.get('join_log_channel_id')
				if join_log_channel is not None:
					try:
						updated_guild = self.bot.get_guild(g.id)
						invites = await updated_guild.invites()
						for invite in invites:
							self.invite_cache[g][invite.code] = invite
					except discord.errors.Forbidden:
						logging.warning(f'logging no view invites perm on {g.name}')

	async def find_possible_invites(self, guild):
		t = 1
		while t < 200:
			updated_invites = await guild.invites()
			res = []
			for invite in updated_invites:
				try:
					old_uses = self.invite_cache[guild][invite.code].uses
				except KeyError:
					self.invite_cache[guild][invite.code] = invite
					if invite.uses >= 1:
						res.append(invite)
					continue

				new_uses = invite.uses
				if old_uses < new_uses:
					self.invite_cache[guild][invite.code] = invite
					res.append(invite)
			if len(res) > 0:
				return res
			else:
				await asyncio.sleep(t)
				t += t
		return None

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(Logging(bot))
