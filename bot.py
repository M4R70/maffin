
from discord.ext import commands
import json
import os
import logging
with open('creds.json','r') as f:
    creds = json.load(f)
    token = creds["token"]

bot = commands.AutoShardedBot(command_prefix='!', formatter=None, description=None, pm_help=False,max_messages=50000)
logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"invite: https://discordapp.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot")
    
    for cog in os.listdir('cogs/'):
        if cog.endswith('.py'):
            cogname = cog[:-3]
            try:
                bot.load_extension("cogs."+cogname)
            except Exception as e:
                print(f"Error loading cog {cogname}" )
                print(e)
                print("""**Traceback:**\n```{0}```\n""".format(' '.join(traceback.format_exception(None, e, e.__traceback__))))
    print("All cogs loaded OK")



bot.run(token)