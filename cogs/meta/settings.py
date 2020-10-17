from discord.ext import commands
from utils.checks import dev
from ruamel import yaml as yaml
import utils.db as db
import pprint
import discord
import logging
from utils.pretty import fake_mention
from utils.checks import is_cog_enabled


def pretty_yaml_dump(dict):
	ugly_yaml = yaml.dump(dict)
	res = []
	for word in ugly_yaml.split(' '):
		if not word.startswith('!!'):
			res.append(word)
	return ' '.join(res)


def embed_list(embed, list, dict=None):
	if dict is None:
		for x in list:
			if x is not None:
				embed.add_field(name=str(x), value="\u200b")
		return embed
	else:
		for k, v in dict.items():
			embed.add_field(name=k, value=v)
		return embed


class Settings(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def allow_disallow_perm(self, name, role, action):
		if name not in [str(x) for x in self.bot.commands]:
			await ctx.send(f"{name} is not a valid command")
			return

		role_id = str(role.id)
		current_perms = await db.get_setting(ctx.guild.id, 'permissions')
		current_perms = current_perms.get(name, [])

		if not isinstance(current_perms, list):
			current_perms = [current_perms]

		if action == "allow":
			if role_id not in current_perms:
				current_perms.append(role_id)
		elif action == "deny":
			if role_id in current_perms:
				current_perms.remove(role_id)
		else:
			logging.warning("allow_disallow on settings cog wrongly used")
			return

		update = {'$set': {name: current_perms}}
		await db.update_setting(ctx.guild.id, 'permissions', update)

	@dev()
	@commands.group()
	async def module(self, ctx):
		"""server specific <cog_name> <enable/disable/list>"""
		if ctx.invoked_subcommand is None:
			await ctx.send('usage example !module <enable/disable> <cogName>')

	@module.command()
	async def enable(self, ctx, cogName):
		await self.module_enable_disable(cogName, ctx, True)

	@module.command()
	async def disable(self, ctx, cogName):
		await self.module_enable_disable(cogName, ctx, False)

	@module.command(aliases=['list'])
	async def module_list(self, ctx):
		enabled = []
		disabled = []
		for x in self.bot.cogs.keys():
			if await is_cog_enabled(x, guild_id=ctx.guild.id):
				enabled.append(x)
			else:
				disabled.append(x)

		if enabled:
			e = discord.Embed()
			e.title = "Enabled Modules:"
			e.colour = discord.Colour.green()
			e = embed_list(e, enabled)
			await ctx.send(embed=e)
		else:
			await ctx.send("No modules enabled")
		if disabled:
			e2 = discord.Embed()
			e2.title = "Disabled Modules"
			e2._colour = discord.Colour.red()
			e2 = embed_list(e2, disabled)
			await ctx.send(embed=e2)
		else:
			await ctx.send('No Modules Disabled')

	async def module_enable_disable(self, cogName, ctx, bool):
		if cogName.lower() not in [x.lower() for x in self.bot.cogs.keys()]:
			await ctx.send('Module is not loaded')
		else:

			await db.update_setting(ctx.guild.id, 'modules_enabled', {'$set': {cogName.lower(): bool}})
			await ctx.send("Done :thumbsup:")

	@commands.command()
	@dev()
	async def update_settings(self, ctx, *, settings):
		dict = yaml.safe_load(settings)
		print(dict)
		for setting, update in dict.items():
			update = {'$set': update}
			await db.update_setting(ctx.guild.id, setting, update)
			await ctx.send("Done :thumbsup:")

	@commands.command()
	@dev()
	async def reset_perms(self, ctx):
		current_perms = await db.get_setting(ctx.guild.id, 'permissions')
		for perm in current_perms.keys():
			if perm not in ['_id','field_name','server_id']:
				await db.update_setting(ctx.guild.id, 'permissions', {'$set': {perm: []}})
		await ctx.send(":thumbsup:")

	@commands.command()
	@dev()
	async def show_settings(self, ctx):  # make this with embeds, no yaml

		all_settings = await db.get_all_settings(ctx.guild.id)
		# del all_settings['permissions']
		# del all_settings['existing_queues']
		# del all_settings['modules_enabled']

		for setting in all_settings:
			del setting['_id']
			name = setting['field_name']
			del setting['field_name']
			e = discord.Embed()
			e.title = name
			embed_list(e, [], dict=setting)
			await ctx.send(embed=e)

	@dev()
	@commands.group()
	async def perms(self, ctx):
		"""server perms <allow/deny> <command_name> <role>"""
		if ctx.invoked_subcommand is None:
			await ctx.send('usage example !perms <allow/deny> <command_name> <role_id>')

	@perms.command()
	async def allow(self, ctx, name: str, role: discord.Role):
		await self.allow_disallow_perm(name, role, "allow")
		await ctx.send("Done :thumbsup:")

	@perms.command()
	async def deny(self, ctx, name: str, role: discord.Role):
		await self.allow_disallow_perm(name, role, "deny")
		await ctx.send("Done :thumbsup:")

	@perms.command()
	async def list(self, ctx, param):

		name = None
		role = None
		perms = await db.get_setting(ctx.guild.id, 'permissions')

		if param in [str(x) for x in self.bot.commands]:
			name = param

		if name is None:
			roles = ctx.guild.roles
			for r in roles:
				if r.id == param or r.name.lower() == param.lower():
					role = r
					break

		if name is None and role is None:
			await ctx.send(f"{param} is not a role or command")
			return

		if name is not None:
			if name not in [str(x) for x in self.bot.commands]:
				await ctx.send(f"{name} is not a valid command")
				return

			print(perms)
			allowed = perms[name]

			if not isinstance(allowed, list):
				allowed = [allowed]

			roles = [ctx.guild.get_role(x) for x in allowed]
			e = discord.Embed()
			e.title = f"Roles allowed to use command {name} are: \n "
			e = embed_list(e, roles)
			msg = ""
			if not allowed:
				msg = "No roles are allowed to use that command"
			await ctx.send(msg, embed=e)
			return

		if role is not None:

			for k, v in perms.items():
				if not isinstance(perms[k], list):
					perms[k] = [v]

			allowed_commands = [x for x in perms.keys() if role.id in perms[x]]
			e = discord.Embed()
			e.title = f"Allowed commands for {role} are: \n"
			e = embed_list(e, allowed_commands)
			msg = ''
			if not allowed_commands:
				msg = f"The role {role} is not authorized to use any commands"
			await ctx.send(msg, embed=e)


def setup(bot):
	bot.add_cog(Settings(bot))
