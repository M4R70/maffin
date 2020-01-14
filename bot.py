from discord.ext import commands
import json
import os
import logging
import traceback

with open('creds.json', 'r') as f:
	creds = json.load(f)
	token = creds["token"]


def load_all_cogs():
	try:
		bot.load_extension('cogs.cogMan')  # first load the cogMan cog
	except Exception as e:
		print("""**Traceback:**\n```{0}```\n""".format(
			' '.join(traceback.format_exception(None, e, e.__traceback__))))
		print(f"Error loading cogMan, Aborting")
		quit()
	try:
		cog_man = bot.cogs['cogMan']
		for cog in os.listdir('cogs/meta'):  # then load the meta cogs
			if cog.endswith('.py'):
				cog_man._load_cog('meta.' + cog[:-3])
		for cog in os.listdir('cogs/dev'):  # then load dev tools
			if cog.endswith('.py'):
				cog_man._load_cog('dev.' + cog[:-3])
		for cog in os.listdir('cogs/feature'):  # lastly, load feature cogs
			if cog.endswith('.py'):
				cog_man._load_cog('feature.' + cog[:-3])
	except Exception as e:
		print("""**Traceback:**\n```{0}```\n""".format(
			' '.join(traceback.format_exception(None, e, e.__traceback__))))
		print(f"Error loading {cog_man.last}, Aborting")
		quit()

	print("Done loading cogs \n \n")


bot = commands.AutoShardedBot(command_prefix='!', formatter=None, description=None, pm_help=False, max_messages=50000)
logging.basicConfig(level=logging.INFO)

load_all_cogs()

@bot.event
async def on_ready():
	print(f" \n \n Logged in as {bot.user}")
	print(f"ID: {bot.user.id}")
	print(f"invite: https://discordapp.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot")
	print("----------READY!---------- \n \n")

bot.run(token)



