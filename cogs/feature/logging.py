from discord.ext import commands, tasks
import utils.db as db
import discord
from utils.checks import is_cog_enabled, dev
import logging
from collections import defaultdict
import timeago
import datetime
import asyncio


async def get_channel(guild, channel_name):
	log_settings = await db.get_setting(guild.id, "logging")
	channel_id = log_settings.get(channel_name)
	channel = guild.get_channel(channel_id)
	if channel_id is not None and channel is None:
		logging.warning(f"can't get channel {channel_id} in {before.guild}")
	return channel


def ow_to_str(x):

	if x is True:
		return "Allow"
	if x is False:
		return "Deny"
	if x is None:
		return "Neutral"


def overwrite_diff(before, after, e):
	before = dict(before)
	after = dict(after)
	before_keys = set(before.keys())
	after_keys = set(after.keys())
	new_keys = after_keys - before_keys
	deleted_keys = before_keys - after_keys
	if len(new_keys) > 0:
		t = 'create'
		for k in new_keys:
			e.add_field(name='Overwrite Added', value=k, inline=False)
			for perm in after[k]:
				if perm[1] is not None:
					e.add_field(name=perm[0], value=ow_to_str(perm[1]),inline=False)
	elif len(deleted_keys) > 0:
		t = 'delete'
		for k in deleted_keys:
			e.add_field(name='Overwrite Removed', value=k, inline=False)
			for perm in before[k]:
				if perm[1] is not None:
					e.add_field(name=perm[0], value=ow_to_str(perm[1]),inline=False)
	else:
		t= 'update'
		for k in after_keys | before_keys:
			if before[k] != after[k]:
				e.add_field(name='Overwrite Updated', value=k.name.replace('@',' '), inline=False)
				for perm in before[k]:
					to = dict(after[k])[perm[0]]
					if perm[1] is not None and perm[1] != to:
						e.add_field(name=perm[0], value=ow_to_str(perm[1]) + '->' + ow_to_str(to),inline=False)

	return t


def member_embed(member, title, color=discord.Colour.blue(), entry=None, mod=True):
	e = discord.Embed()
	e.colour = color
	e.title = title
	e.set_author(name=member.display_name, icon_url=member.avatar_url)
	# e.add_field(name="User", value=member.name, inline=True)
	e.add_field(name="User ID", value=member.id, inline=False)
	# e.add_field(name="\u200b", value="\u200b", inline=False)
	if mod:
		add_mod(entry, e)
	return e


def add_mod(entry, e):
	if entry is not None:
		e.add_field(name="Moderator", value=f"{entry.user}")
		e.add_field(name="Moderator ID", value=str(entry.user.id))
	# e.add_field(name="\u200b", value="\u200b", inline=False)
	else:
		e.add_field(name="Moderator", value="failed to obtain", inline=False)


async def search_entry(guild, target_user, action):
	t = 1
	entry = None
	while entry is None:
		async for e in guild.audit_logs(action=action, limit=10):
			if e.target.id == target_user.id:
				if entry.user is not None and entry.user == self.bot.user:
					entry.user = self.bot.cogs['Moderation'].mod_register[str(action)].pop(user.id,self.bot.user)
				return e
		await asyncio.sleep(t)
		t += t
		if t > 60:
			return None


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

		e = member_embed(member, title="Joined", color=discord.Colour.teal(), mod=False)

		if possible_invites is None:
			e.add_field(name="Invite could not be retrieved", value=nothing, inline=False)
		
		elif len(possible_invites) == 1:
			e.add_field(name="Acount created", value=timeago.format(member.created_at, datetime.datetime.now()))
			e.add_field(name="Invite used", value=possible_invites[0].url, inline=False)
			e.add_field(name="Invite created by", value=str(possible_invites[0].inviter), inline=True)
			e.add_field(name="Number of uses", value=str(possible_invites[0].uses), inline=True)

		elif len(possible_invites) > 1:
			e.add_field(name="Possible invites used:", value=nothing, inline=False)
			for i in possible_invites:
				e.add_field(name=nothing, value=i.url, inline=False)
		else:
			return

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

		e = member_embed(member, title="Left", color=discord.Colour.red(), mod=False)

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
			e.add_field(name="Message", value=f"{message.content}" + "\u200b", inline=False)
		else:
			e.add_field(name="Message", value=f"Message too long, will be posted below this", inline=False)
			post_separate = True
		await channel.send(embed=e)
		if post_separate:
			await channel.send(f"```{message.content}```")

	@commands.Cog.listener()
	async def on_guild_role_delete(self, role):
		channel = await get_channel(role.guild, 'role_log_channel_id')
		if channel is None:
			return

		entry = await search_entry(role.guild, role, discord.AuditLogAction.role_delete)
		e = discord.Embed()
		e.title = "Role Deleted"
		e.colour = role.colour
		e.add_field(name="Role", value=str(role))
		add_mod(entry, e)
		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_guild_role_create(self, role):
		channel = await get_channel(role.guild, 'role_log_channel_id')
		if channel is None:
			return
		important_perms = {'kick_members', 'ban_members', 'administrator', 'administrator', 'manage_guild',
						   'manage_messages', 'mention_everyone', 'mute_members', 'deafen_members', 'move_members',
						   'manage_nicknames', 'manage_roles', 'manage_webhooks', 'manage_emojis'}

		important = [p[0] for p in role.permissions if p[1] and p[0] in important_perms]

		entry = await search_entry(role.guild, role, discord.AuditLogAction.role_create)
		e = discord.Embed()
		e.title = "Role Created"
		e.colour = role.colour
		e.add_field(name="Role", value=str(role), inline=False)
		add_mod(entry, e)

		e.add_field(name="Important Permissions", value=f"""{' || '.join(important)}""", inline=False)
		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_guild_role_update(self, before, after):
		channel = await get_channel(before.guild, 'role_log_channel_id')
		if channel is None:
			return

		if before.permissions != after.permissions:
			before_perms = {p[0] for p in before.permissions if p[1]}
			after_perms = {p[0] for p in after.permissions if p[1]}
			lost = []
			gained = []
			for perm in before_perms.union(after_perms):
				if perm in before_perms and perm not in after_perms:
					lost.append(perm)
				elif perm not in before_perms and perm in after_perms:
					gained.append(perm)

			entry = await search_entry(before.guild, after, discord.AuditLogAction.role_update)
			e = discord.Embed()
			e.title = "Role Permissions Updated"
			e.add_field(name="Role", value=str(after), inline=False)
			add_mod(entry, e)
			if len(gained) > 0:
				e.add_field(name="Permissions Gained", value=f"""{' || '.join(gained)}""", inline=False)
			if len(lost) > 0:
				e.add_field(name="Permissions Gained", value=f"""{' || '.join(lost)}""", inline=False)

			e.colour = after.colour
			await channel.send(embed=e)



	@commands.Cog.listener()
	async def on_guild_channel_update(self, before, after):
		channel = await get_channel(after.guild, 'channel_log_channel_id')
		if channel is None:
			return

		if before.overwrites != after.overwrites:
			e = discord.Embed()
			e.title = "Channel Permissions Updated"
			e.add_field(name="Channel", value=str(after), inline=False)

			t = overwrite_diff(before.overwrites, after.overwrites, e)
			if t == "create":
				action = discord.AuditLogAction.overwrite_create
			elif t == "delete":
				action = discord.AuditLogAction.overwrite_delete
			elif t == "update":
				action = discord.AuditLogAction.overwrite_update
			entry = await search_entry(after.guild,after,action)
			add_mod(entry, e)
			await channel.send(embed=e)

		if before.name != after.name:
			e = discord.Embed()
			e.title = "Channel Renamed"
			e.add_field(name="Old Name", value=str(before),inline=False)
			e.add_field(name="New Name", value=str(after), inline=False)
			entry = await search_entry(after.guild,after,discord.AuditLogAction.channel_update)
			add_mod(entry, e)
			await channel.send(embed=e)




	@commands.Cog.listener()
	async def on_guild_channel_create(self, new_channel):
		channel = await get_channel(new_channel.guild, 'channel_log_channel_id')
		if channel is None:
			return
		e = discord.Embed()
		e.title = "Channel Created"
		e.add_field(name="Channel", value=str(new_channel),inline=False)
		entry = await search_entry(new_channel.guild, new_channel, discord.AuditLogAction.channel_create)
		add_mod(entry, e)
		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_guild_channel_delete(self, del_channel):
		channel = await get_channel(del_channel.guild, 'channel_log_channel_id')
		if channel is None:
			return
		e = discord.Embed()
		e.title = "Channel Deleted"
		e.add_field(name="Channel", value=str(del_channel),inline=False)
		entry = await search_entry(del_channel.guild, del_channel, discord.AuditLogAction.channel_delete)
		add_mod(entry, e)
		await channel.send(embed=e)

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
			e = member_embed(member,diff)

		await channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_update(self, before, after):

		e = member_embed(after, color=discord.Colour.purple(), title='asd')
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
	@commands.command(hidden=True)
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
