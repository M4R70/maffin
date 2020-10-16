from discord.ext import commands
import discord
import json
import logging
from utils.exceptions import report_meta
import sys
import traceback

# import utils.db


intents = discord.Intents.default()
intents.members = True

with open('creds.json', 'r') as f:
	creds = json.load(f)
	token = creds["token"]


async def load_all_cogs():
	try:
		bot.load_extension('cogs.meta.cogMan')  # first load the cogMan cog
	except Exception as e:
		await report_meta(e)
		quit()

	try:
		cogMan = bot.cogs['cogMan']
		logging.info("loaded cogMan")
		await cogMan.load_all_cogs()
	except Exception as e:
		await report_meta(e)


bot = commands.AutoShardedBot(command_prefix='!', formatter=None, description=None, pm_help=False,
							  max_messages=50000, intents=intents,guild_subscriptions=True,fetch_offline_members=True)

logging.basicConfig(level=logging.INFO)


@bot.event
async def on_ready():
	logging.info(f" \n \n Logged in as {bot.user}")
	logging.info(f"ID: {bot.user.id}")
	logging.info(f"invite: https://discordapp.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot")
	await load_all_cogs()
	logging.info("----------READY!---------- \n \n")


@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.errors.CheckFailure):
		pass
	else:
		print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


bot.run(token)

# async def get_pre(bot, message):
# 	default_prefix = '!'
# 	res = [f"<@!{bot.user.id}> "]
# 	db_info = await utils.db.findOne('prefixes', {'guild_id': message.guild.id})
# 	if db_info is None:
# 		res.append(default_prefix)
# 	else:
# 		res.append(db_info['prefix'])
#
# 	return res
