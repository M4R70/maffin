from discord.ext import commands
import utils.db as db
import discord
import random
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev


class Deployment(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@dev()
	@commands.command()
	async def set_host(self, ctx, role: discord.Role):
		"""shortcut to set target role as host"""
		current_perms = await db.get_setting(ctx.guild.id, 'permissions')

		admin_commands = ['qcreate', 'qdelete']

		cmds = [x.name for x in self.bot.cogs['Queues'].get_commands()]

		for command in cmds:
			command = str(command).lower()
			if command not in admin_commands:
				if command not in current_perms.keys():

					current_perms[command] = []
				elif not isinstance(current_perms[command], list):

					current_perms[command] = [current_perms[command]]
				else:
					current_perms[command].append(role.id)
				update = {'$set': {command: current_perms[command]}}
				await db.update_setting(ctx.guild.id, 'permissions', update)

		await ctx.send("Done :thumbsup:")

	@dev()
	@commands.command()
	async def create_log_category(self, ctx):
		"""sets up a category for the log channels"""
		log_channels = ['ban', 'voice', 'role', 'mute', 'join', 'text']

		try:
			category = await ctx.guild.create_category_channel('Maffin Logs', position=0)
			for channel_name in log_channels:
				channel = await category.create_text_channel(channel_name)
				field = channel_name + '_log_channel_id'
				await db.update_setting(ctx.guild.id, 'logging', {"$set": {field: channel.id}})
			await ctx.send("Done (check top of channel list, and remember LOG CHANNELS ARE CREATED PUBLIC )")
		except discord.errors.Forbidden:
			await ctx.send("ERROR: bot missing perms :(")
		return


def setup(bot):
	bot.add_cog(Deployment(bot))
