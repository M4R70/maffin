from discord.ext import commands
import discord
import asyncio
import timeago
import datetime


class logs(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.invites = {}
		self.crawler = self.bot.loop.create_task(self.crawl_invites())
		self.valid_channels = [
			"vc_log_channel",
			"ban_log_channel",
			"join_log_channel",
			"member_update_log_channel",
			"text_chat_log_channel",
			"mute_log_channel"
		]
		self.errorCog = self.bot.cogs["errorHandling"]

	async def try_to_send(channel, message, embed, cog):
		pass

	def validate_settings(self, settings, guild):
		try:
			if settings["enabled"]:

				try:
					channels = settings['channels']
				except KeyError:
					return f"logs, Missing field Channels"

				for channel in self.valid_channels:
					try:
						menu_entry = settings["channels"][channel]
						if not menu_entry == "disabled":
							actual_channel = guild.get_channel(settings["channels"][menu_entry])
							if actual_channel == None:
								return f"logs: {channel} not found"
					except KeyError:
						pass

		# vc_log_channel = guild.get_channel(settings["channels"]["vc_log_channel"])
		# if vc_log_channel == None:
		# 	return "logs: vc log channel not found"
		# ban_log_channel = guild.get_channel(settings["channels"]["ban_log_channel"])
		# if ban_log_channel == None:
		# 	return "logs: ban log channel not found"
		# join_log_channel = guild.get_channel(settings["channels"]["join_log_channel"])
		# if join_log_channel == None:
		# 	return "logs: join log channel not found"
		# member_update_log_channel = guild.get_channel(settings["channels"]["member_update_log_channel"])
		# if member_update_log_channel == None:
		# 	return "logs: member update log channel not found"
		# text_chat_log_channel = guild.get_channel(settings["channels"]["text_chat_log_channel"])
		# if text_chat_log_channel == None:
		# 	return "logs: text chat log channel not found"

		except KeyError as e:
			return f"logs: Missing field: enabled"

		return True

	# on_message_edit(before, after)

	async def get_channel_if_enabled(self, guild, channel_name):
		settings = await self.bot.cogs["Settings"].get(guild.id, "logs")
		try:
			if not settings['enabled']:
				return False
		except (ValueError, KeyError):
			return False

		try:
			if settings["channels"][channel_name] == "disabled":
				return False
		except KeyError:
			return False

		else:
			actual_channel = guild.get_channel(settings["channels"][channel_name])
			if actual_channel == None:
				return False
			else:
				return actual_channel


	@commands.Cog.listener()
	async def on_message_edit(self, before, after):
		channel = await self.get_channel_if_enabled(before.guild, "text_chat_log_channel")
		if channel == False:
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
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")
		except discord.errors.HTTPException:
			pass

	@commands.Cog.listener()
	async def on_message_delete(self, message):
		channel = await self.get_channel_if_enabled(message.guild, "text_chat_log_channel")
		if channel == False:
			return

		entry = await search_entry(message.guild, message.author, discord.AuditLogAction.message_delete)
		e = member_embed(message.author, color=discord.Colour.dark_orange(), title="Message Deleted", entry=entry)

		post_separate = False
		if len(message.content) < 1000:
			e.add_field(name="Message", value=f"{message.content}", inline=False)
		else:
			e.add_field(name="Message", value=f"Message too long, will be posted below this", inline=False)
			post_separate = True

		try:

			await channel.send(embed=e)
			if post_separate:
				await channel.send(f"```{message.content}```")

		except discord.Forbidden:
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")
		except discord.errors.HTTPException:
			pass

	@commands.Cog.listener()
	async def on_member_update(self, before, after):
		channel = await self.get_channel_if_enabled(before.guild, "member_update_log_channel")
		if channel == False:
			return

		e = member_embed(after, color=discord.Colour.purple())
		post = False

		if before.display_name != after.display_name:
			e.title = "Name Change"
			e.add_field(name="Old", value=f"{before.display_name}", inline=False)
			e.add_field(name="new", value=f"{after.display_name}", inline=False)
			post = True
		elif before.roles != after.roles:
			pass  # TODO roles
		if post:
			try:
				await channel.send(embed=e)
			except discord.Forbidden:
				await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	# @commands.Cog.listener()
	# async def on_user_update(self,before, after):
	# 	channel = await self.get_channel_if_enabled(before.guild,"member_update_log_channel")
	# 	if channel == False:
	# 		return

	# 	e = member_embed(after,color=discord.Colour.purple())

	# 	post = False
	# 	if before.avatar_url != after.avatar_url:
	# 		e.title = "Avatar Change"
	# 		e.add_field(name="Old",value=f"{before.avatar_url}",inline=False)
	# 		e.add_field(name="new",value=f"{after.avatar_url}",inline=False)
	# 		post = True
	# 	elif before.display_name != after.display_name:
	# 		e.title = "Name Change"
	# 		e.add_field(name="Old",value=f"{before.display_name}",inline=False)
	# 		e.add_field(name="new",value=f"{after.display_name}",inline=False)
	# 		post = True
	# 	if post:
	# 		await channel.send(embed=e)

	async def log_server_mute(self, diff, member):
		channel = await self.get_channel_if_enabled(member.guild, "mute_log_channel")
		if channel == False:
			return

		entry = await search_entry(member.guild, member, discord.AuditLogAction.member_update)

		if diff == "Muted":
			color = discord.Colour.orange()
		else:
			color = discord.Colour.gold()

		e = None

		e = member_embed(member, title=f"{diff}", color=color, entry=entry)

		try:
			await channel.send(embed=e)
		except discord.Forbidden:
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		channel = await self.get_channel_if_enabled(member.guild, "vc_log_channel")
		if channel == False:
			return

		diff = voice_state_diff(before, after)

		if diff == None:
			return

		elif diff == "Muted" or diff == "Unmuted":
			await self.log_server_mute(diff, member)
			return
		else:
			e = member_embed(member)
			e.title = diff
			try:
				await channel.send(embed=e)
			except discord.Forbidden:
				await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	@commands.Cog.listener()
	async def on_member_ban(self, guild, user):
		channel = await self.get_channel_if_enabled(guild, "ban_log_channel")
		if channel == False:
			return

		entry = await search_entry(guild, user, discord.AuditLogAction.ban)
		e = member_embed(user, title="BAN", color=discord.Colour.red(), entry=entry)
		ask_for_reason = False

		e.add_field(name="Reason", value=entry.reason)

		try:
			message = await channel.send(embed=e)
			if entry.reason is None:
				await self.do_ask_for_reason(entry, message, user)
			else:
				print(entry.reason)
		except discord.Forbidden:
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	async def do_ask_for_reason(self, entry, message, user):
		mod = entry.user
		if mod is not None:
			await mod.send(
				f"Hey, you banned {str(user)} from {str(message.guild)} but you specified no reason. \n\nTo add one,"
				f" send me the command `!add_reason {message.id} <reason> ` "
				f"\n\nNote that you must send this command in the guild, and not here in DMs")

	@commands.has_permissions(ban_members=True)
	@commands.guild_only()
	@commands.command()
	async def add_reason(self, ctx, message_id: int, *, reason: str):
		channel = await self.get_channel_if_enabled(ctx.guild, "ban_log_channel")
		if not channel:
			return
		message = await channel.fetch_message(message_id)
		e = message.embeds[0]
		e.set_field_at(-1,name="Reason",value=reason,inline=False)
		await message.edit(embed=e)
		await ctx.send("Reason updated!")

	@commands.Cog.listener()
	async def on_member_unban(self, guild, user):
		channel = await self.get_channel_if_enabled(guild, "ban_log_channel")
		if channel == False:
			return

		entry = await search_entry(guild, user, discord.AuditLogAction.unban)
		e = member_embed(user, title="UNBAN", color=discord.Colour.green(), entry=entry)
		try:
			await channel.send(embed=e)
		except discord.Forbidden:
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	@commands.Cog.listener()
	async def on_member_remove(self, member):
		channel = await self.get_channel_if_enabled(member.guild, "join_log_channel")
		if channel == False:
			return

		nothing = "** **"

		e = discord.Embed()
		e.colour = discord.Colour.dark_grey()
		e.title = f"{member}"
		e.set_author(name="Member Left", icon_url=member.avatar_url)
		e.add_field(name="ID:", value=member.id)
		try:
			await channel.send(embed=e)
		except:
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	@commands.Cog.listener()
	async def on_member_join(self, member):
		channel = await self.get_channel_if_enabled(member.guild, "join_log_channel")
		if channel == False:
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
			await self.errorCog.report("logs", f"Missing permission to post in {channel.name}")

	async def crawl_invites(self):
		await self.bot.wait_until_ready()
		while True:
			for guild in self.bot.guilds:
				try:
					guild_invites = {}
					invites = await guild.invites()
					for invite in invites:
						guild_invites[invite.code] = invite
					self.invites[guild] = guild_invites
				except discord.errors.Forbidden:
					pass
			await asyncio.sleep(60 * 10)

	async def find_possible_invites(self, guild):
		t = 1
		while t < 200:
			new = await guild.invites()
			res = []
			for invite in new:
				try:
					old_uses = self.invites[guild][invite.code].uses
				except KeyError:
					self.invites[guild][invite.code] = invite
					if invite.uses >= 1:
						res.append(invite)
					continue

				new_uses = invite.uses
				if old_uses < new_uses:
					self.invites[guild][invite.code] = invite
					res.append(invite)

			if res == []:
				await asyncio.sleep(t)
				t += t
			else:
				return res
		return None


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


def setup(bot):
	bot.add_cog(logs(bot))
