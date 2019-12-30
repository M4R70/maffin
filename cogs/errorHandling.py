from discord.ext import commands
from discord import client
import discord
import asyncio
import timeago
import datetime

class errorHandling(commands.Cog):
	def __init__(self,bot):
		self.bot = bot

	def validate_settings(self,settings,guild):
		return True

	async def report(self, cog, message):

		print(f"errorHandling: {cog}: " + message)

	async def dev_report(self, cog, message):

		print(f"dev: {cog}: " + message)

	async def try_to_send(channel,cog,text=None,embed=None,file=None):
		await channel.send(content=message,embed=embed)

	
	# @commands.Bot.event()
	# async def on_error(self,event, *args, **kwargs):
	# 	print("error!")



def setup(bot):
	bot.add_cog(errorHandling(bot))