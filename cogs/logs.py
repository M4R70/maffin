from discord.ext import commands
import discord
import asyncio
import timeago
import datetime

class logs(commands.Cog):
	def __init__(self,bot):
		self.bot = bot
		self.open_cases = []
		self.invites = {}
		self.crawler = self.bot.loop.create_task(self.crawl_invites())


	def validate_settings(self,settings,guild):
		try: 
			if settings["enabled"]:
				vc_log_channel = guild.get_channel(settings["vc_log_channel"])
				if vc_log_channel == None:
					return "logs: vc log channel not found"
				ban_log_channel = guild.get_channel(settings["ban_log_channel"])
				if ban_log_channel == None:
					return "logs: ban log channel not found"					
				join_log_channel = guild.get_channel(settings["join_log_channel"])
				if join_log_channel == None:
					return "logs: join log channel not found"
				member_update_log_channel = guild.get_channel(settings["member_update_log_channel"])
				if member_update_log_channel == None:
					return "logs: member_update log channel not found"			


				# pingRole = [r for r in guild.roles if r.id == settings['role_id']]
				# if len(pingRole) == 0:
				# 	return "staffPing: role not found"
				# pingChannel = guild.get_channel(settings["channel_id"])
				# if pingChannel == None:
				# 	return "staffPing: channel not found"
		
		except KeyError as e:
			return f"logs, Missing field {e}"
		
		return True
		
	

	@commands.Cog.listener()
	async def on_member_update(self,before, after):
		settings = await self.bot.cogs["Settings"].get(before.guild.id,"logs")
		if not settings['enabled']:
			return
		
		e = member_embed(after,color=discord.Colour.purple)


		if before.status != after.status:
			e.title = "Status Change"
			e.add_field(name="Old",value=f"{before.status}",inline=False)
			e.add_field(name="new",value=f"{after.status}",inline=False)
		elif before.display_name != after.display_name:
			e.title = "Name Change"
			e.add_field(name="Old",value=f"{before.display_name}",inline=False)
			e.add_field(name="new",value=f"{after.display_name}",inline=False)
		elif before.roles != after.roles:
			e = await search_entry(after.guild,after,AuditLogAction.member_role_update) #ojo, que puede ganar/perder muchos roles en poco tiempo!







	@commands.Cog.listener()
	async def on_voice_state_update(self,member, before, after):
		settings = await self.bot.cogs["Settings"].get(member.guild.id,"logs")
		if not settings['enabled']:
			return
		e = member_embed(member)
		e.title = voice_state_diff(before,after)
		
		vc_log_channel = member.guild.get_channel(settings["vc_log_channel"])
		await vc_log_channel.send(embed=e)


	@commands.Cog.listener()
	async def on_member_ban(self, guild, user):
		settings = await self.bot.cogs["Settings"].get(guild.id,"logs")
		if not settings['enabled']:
			return
		
		entry = await search_entry(guild,user,discord.AuditLogAction.ban)
		
		ban_log_channel = guild.get_channel(settings["ban_log_channel"])
		e = None
		if entry == "fail":
			e = member_embed(user,title="BAN",color=discord.Colour.red())
			e.add_field(name="Moderator",value="failed to obtain")
		else:
			e = member_embed(user,title="BAN",color=discord.Colour.red(),entry=entry)
			if entry.reason == None:
				pass #TODO romperle las bolas al mod para que agregue razon
		await ban_log_channel.send(embed=e)


	@commands.Cog.listener()
	async def on_member_unban(self,guild, user):
		settings = await self.bot.cogs["Settings"].get(guild.id,"logs")
		if not settings['enabled']:
			return
		
		entry = await search_entry(guild,user,discord.AuditLogAction.unban)
		ban_log_channel = guild.get_channel(settings["ban_log_channel"])

		if entry == "fail":
			e = member_embed(user,title="UNBAN",color=discord.Colour.green())
			e.add_field(name="Moderator",value="failed to obtain")
		else:
			e = member_embed(user,title="UNBAN",color=discord.Colour.green(),entry=entry,no_reason=True)

		await ban_log_channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_remove(self,member):
		settings = await self.bot.cogs["Settings"].get(member.guild.id,"logs")
		if not settings['enabled']:
			return
		nothing = "** **"
		join_log_channel = member.guild.get_channel(settings["join_log_channel"])
		e = discord.Embed()
		e.colour = discord.Colour.dark_grey()
		e.title = f"{member}"
		e.set_author(name="Member Left",icon_url=member.avatar_url)	
		e.add_field(name="ID:",value=member.id)

		await join_log_channel.send(embed=e)

	@commands.Cog.listener()
	async def on_member_join(self,member):
		settings = await self.bot.cogs["Settings"].get(member.guild.id,"logs")
		if not settings['enabled']:
			return

		join_log_channel = member.guild.get_channel(settings["join_log_channel"])

		possible_invites = await self.find_possible_invites(member.guild)
		nothing = "** **"

		e = discord.Embed()
		e.colour = discord.Colour.teal()
		e.title = f"{member}"
		e.set_author(name="Member Joined",icon_url=member.avatar_url)	
		e.add_field(name="ID:",value=member.id)
		
		if len(possible_invites) == 1:
			e.add_field(name="Acount created",value=timeago.format(member.created_at, datetime.datetime.now()))
			e.add_field(name="Invite used",value=possible_invites[0].url,inline=False)
			e.add_field(name="Invite created by",value=str(possible_invites[0].inviter),inline=True)
			e.add_field(name="Number of uses",value=str(possible_invites[0].uses),inline=True)

			
		elif len(possible_invites) > 1:
			e.add_field(name="Possible invites used:",value=nothing,inline=False)
			for i in possible_invites:
				e.add_field(name=nothing,value=i.url,inline=False)
		else:
			e.add_field(name="Invite could not be retrieved",value=nothing,inline=False)

		await join_log_channel.send(embed=e)


	async def crawl_invites(self):
		for guild in self.bot.guilds:
			try:
				guild_invites = {}
				invites = await guild.invites()
				for invite in invites:
					guild_invites[invite.code] = invite
				self.invites[guild] = guild_invites
			except discord.errors.Forbidden:
				pass
		await asyncio.sleep(600)

	async def find_possible_invites(self,guild):
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
				if old_uses < new_uses :
					self.invites[guild][invite.code] = invite
					res.append(invite)

			if res == []:
				await asyncio.sleep(t)
				t+=t
			else:
				return res
		return None


async def search_entry(guild,target_user,action):
	t = 1
	entry = None
	while entry == None:
		async for e in guild.audit_logs(action=action,limit=10):
			if e.target.id == target_user.id:
				return e
		await asyncio.sleep(t)
		t += t
		if t > 200:
			return "fail"


def voice_state_diff(before,after):
	if before.channel != after.channel:
		if before.channel == None or before.afk:
			return f"connected to {after.channel.name}"
		if after.channel == None:
			return f"disconnected from {before.channel}"
		else:
			return f"moved from {before.channel.name} to {after.channel.name}"




def member_embed(member, title="Insert a title you lazy dev!",color = discord.Colour.blue(),entry=None,no_reason=False):
	e = discord.Embed()
	e.colour = color
	e.title = title
	e.set_author(name=member.display_name, icon_url=member.avatar_url)
	e.add_field(name="Account name",value=member.name,inline=True)
	e.add_field(name="User id",value=member.id,inline=True)
	if entry != None:
		e.add_field(name="Moderator",value=f"{entry.user}",inline=False)
		if not no_reason:
			e.add_field(name="Reason",value=f"{entry.reason}")
	return e


def setup(bot):
    bot.add_cog(logs(bot))