from discord.ext import commands

import discord
#import asyncio
#import timeago
import datetime
import timedelta
import utils.db
from utils.checks import dev
import seaborn as sns
from matplotlib import pyplot as plt
import pandas as pd

class analytics(commands.Cog):
	
	def __init__(self,bot):
		self.bot = bot
		self.converter = commands.MemberConverter()
	
	def validate_settings(self,settings,guild):
			try: 
				if settings["enabled"]:
					pass

			except KeyError as e:
				return f"logs, Missing field {e}"

			return True

	@commands.Cog.listener()
	async def on_message(self,message):
		
		settings = await self.bot.cogs["Settings"].get(message.guild.id,"analytics")
		if not settings['enabled']:
			return        
		
		data = {
			"author_id" : message.author.id,
			"text_channel_id" : message.channel.id ,
			"guild_id" : message.guild.id,
			"length" : len(message.content) ,
			"datetime" : datetime.datetime.now(),
			"qj" : False ,
			"qn" : False ,
		} 

		if message.content == "!qj":
			data["qj"] = True
		elif message.content == "!qn":
			data["qn"] = True
		
		await utils.db.insertOne(f"analytics.text.a{message.guild.id}", data)
	

	# @commands.command()
	# async def get_settings(self,ctx,*,cogName=None):
	@dev() #temp!
	@commands.command()
	async def info(self,ctx,*args):

		n , member = await self.parse_params(ctx,args)
		
		now = datetime.datetime.now()

		query = {
			"datetime" : {
				"$lt" : now,
				"$gte" : now - timedelta.Timedelta(days=n)
			},
			"author_id" : member.id,
			"guild_id" : member.guild.id

		}

		data = await utils.db.find(f"analytics.text.a{member.guild.id}",query)

		days = [now.date()]

		for i in range(1,n+1):
			days.append((now - timedelta.Timedelta(days=i)).date())

		
		days = list(reversed(days))



		columns=['#Messages','#Characters',"#qj","#qn"]
		df = pd.DataFrame(index=days)
		for c in columns:
			df[c] = 0
		
		for datapoint in data:
			day = datapoint['datetime'].date()
			
			df['#Messages'][day] += 1

			
			df['#Characters'][day] += datapoint['length']
			
			if datapoint['qn']:
				df['#qn'][day] += 1
			
			elif datapoint['qj']:
				df['#qj'][day] += 1

			

		




		plt.clf()
		plot = df.plot.bar(y="#Messages")
		# plot.set(xticks=days)
		plt.xticks(rotation=90)
		fig = plot.get_figure()
		fig.savefig("output.png")

		plt.clf()

		plot = df.plot.bar(y="#Characters")
		# plot.set(xticks=days)
		plt.xticks(rotation=90)
		fig = plot.get_figure()
		fig.savefig("output2.png")
		


		

		


		#print(data)



	async def parse_params(self,ctx,args):
			n = None
			member = None
			for a in args:
				if member == None:
					try:
						member = await self.converter.convert(ctx,a)
						continue
					except discord.ext.commands.errors.BadArgument as e :
						pass
				
				if n == None:
					try:
						n = int(a)
						if len(str(n)) > 13:
							n = None
					except (ValueError, OverflowError):
						pass
						
			if n == None:
				n = 30
			if member == None:
				member = ctx.author 

			return n,member

# db.system.profile.find({ 
#   "timestamp" : { 
#     $lt: new Date(), 
#     $gte: new Date(new Date().setDate(new Date().getDate()-1))
#   }   
# })

	

	# @commands.Cog.listener()
	# async def on_voice_state_update(self,member, before, after):
	# 	settings = await self.bot.cogs["Settings"].get(member.guild.id,"logs")
	# 	if not settings['enabled']:
	# 		return
	# 	e = member_embed(member)
	# 	e.title = voice_state_diff(before,after)
		
	# 	vc_log_channel = member.guild.get_channel(settings["vc_log_channel"])
	# 	await vc_log_channel.send(embed=e)


# def voice_state_diff(before,after):
# 	if before.channel != after.channel:
# 		if before.channel == None or before.afk:
# 			return f"connected to {after.channel.name}"
# 		if after.channel == None:
# 			return f"disconnected from {before.channel}"
# 		else:
# 			return f"moved from {before.channel.name} to {after.channel.name}"


def setup(bot):
	bot.add_cog(analytics(bot))