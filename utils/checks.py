from discord.ext import commands
import discord
import utils.db as db
import logging


def dev():
	def predicate(ctx):
		return ctx.message.author.id == 219632772514316289

	return commands.check(predicate)


def has_roles(user, role_ids):
	if role_ids is None:
		return False
	if not isinstance(role_ids, list):
		role_ids = [role_ids]

	for role_id in role_ids:
		if str(role_id) in [str(r.id) for r in user.roles]:
			return True

	return False


async def is_host(guild_id, user):
	config = await db.get_setting(guild_id, 'permissions')
	allowed_roles = config['qlock']
	res = has_roles(user, allowed_roles)
	return res


async def is_cog_enabled(ctx,guild_id=None):

	try:
		if hasattr(ctx,'guild'):
			config = await db.get_setting(ctx.guild.id, 'modules_enabled')
			return config[ctx.command.cog_name.lower()]
		else:
			config = await db.get_setting(guild_id, 'modules_enabled')
			return config[ctx.lower()]
	except KeyError:
		return True


def is_allowed_in_config():
	async def predicate(ctx):
		config = await db.get_setting(ctx.guild.id, 'permissions')

		allowed_roles = config.get(ctx.command.name)
		res = has_roles(ctx.author, allowed_roles)
		if res:
			return True
		else:
			# await ctx.send("You are not authorized to do this")
			return False

	return commands.check(predicate)
