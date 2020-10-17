from discord.ext import commands
import utils.db as db
import discord
from utils.checks import , is_cog_enabled,dev




class Logging(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.invite_cache = {}
		self.crawl_invites.start()

	@tasks.loop(minutes=10)
	async def crawl_invites(self):
		await self.bot.wait_until_ready()
		for g in self.bot.guilds:
			if is_cog_enabled(g.id):
				settings = await db.get_setting(g.id,'logging')
				join_log_channel = settings.get('join_log_channel_id')
				if join_log_channel is not None:
					try:
						updated_guild = self.bot.get_guild(g.id)
						invites = await updated_guild.invites()
						for invite in invites:
							self.invite_cache[invite.code] = invite
					except discord.errors.Forbidden:


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


	def cog_unload(self):
		self.crawl_invites.start().cancel()

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(Logging(bot))
