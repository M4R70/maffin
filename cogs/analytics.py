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
		self.dynamic_connection_data = {}
	
	def validate_settings(self,settings,guild):
			try: 
				if settings["enabled"]:
					pass

			except KeyError as e:
				return f"logs, Missing field {e}"

			return True

	

#moved, disconnected, connected

	@commands.Cog.listener()
	async def on_voice_state_update(self,member, before, after):
		settings = await self.bot.cogs["Settings"].get(member.guild.id,"logs")
		if not settings['enabled']:
			return
		
		action = voice_state_diff(before,after)


		now = datetime.datetime.now()
		if action == "connected":
			await self.log_connection(member,now)
		elif action == "disconnected":
			await self.log_disconnection(member,before.channel,now)
		elif action == "move":
			await self.log_disconnection(member,before.channel,now)
			await self.log_connection(member,now)
			


	async def log_connection(self,member,now):
		try:
			self.dynamic_connection_data[member.guild.id][member.id] = now
		except KeyError:
			self.dynamic_connection_data[member.guild.id] = {}
			self.dynamic_connection_data[member.guild.id][member.id] = now

	async def log_disconnection(self,member,channel,now):
		try:
			start = self.dynamic_connection_data[member.guild.id][member.id]
			del self.dynamic_connection_data[member.guild.id][member.id]
		except KeyError:
			return


		connection_time = now - start

		d = {
			"member_id" : member.id,
			"voice_channel id" : channel.id,
			"guild_id" : member.guild.id,
			"length_mins" : connection_time.total_seconds() / 60,
			"datetime" : now
		}

		await utils.db.insertOne(f"analytics.voice.a{member.guild.id}",d)
	
	@commands.Cog.listener()
	async def on_message(self,message):
		
		settings = await self.bot.cogs["Settings"].get(message.guild.id,"analytics")
		if not settings['enabled']:
			return        
		
		data = {
			"member_id" : message.author.id,
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
	# async def t(self,ctx,*args):

	# 	n , member = await self.parse_params(ctx,args)
	# 	now = datetime.datetime.now()
	# 	now_naive_utc = make_naive(now)

	# 	days = [now.date()]
		
	# 	for i in range(1,n+1):
	# 		days.append((now - timedelta.Timedelta(days=i)).date())

	# 	days = list(reversed(days))
	# 	df = pd.DataFrame(index=days)
	# 	columns=['#Messages','#Characters']
	# 	for c in columns:
	# 		df[c] = 0


	# 	after = now  - timedelta.Timedelta(days=n)
	# 	count = 0
	# 	for channel in ctx.guild.text_channels:
	# 		try:
	# 			print(channel.name)
	# 			async for message in channel.history(after=after,limit=None) :
	# 				count += 1
	# 				if message.author.id == member.id:
	# 					try:
	# 						day = message.created_at.date()
	# 						df["#Messages"][day] += 1
	# 						df["#Characters"][day]  += len(message.content)
	# 					except:
	# 						print("caca")
	# 						return

	# 		except:
	# 			#print("Error accesing " + channel.name)
	# 			pass

			
	# 	print(count)
	# 	bar_plot(df[["#Characters","#Messages"]],"g1.png",palette="hls")

	# 	with open('g1.png','rb') as f:
	# 		fi = discord.File(f,filename='Activity Graph.png')
	# 		await ctx.send("User data for " + member.display_name + ":",file=fi)

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
			"member_id" : member.id,
			"guild_id" : member.guild.id
		}

		text_data = await utils.db.find(f"analytics.text.a{member.guild.id}",query)
		voice_data = await utils.db.find(f"analytics.voice.a{member.guild.id}",query)

		days = [now.date()]

		for i in range(1,n+1):
			days.append((now - timedelta.Timedelta(days=i)).date())

		
		days = list(reversed(days))



		columns=['#Messages','#Characters',"#qj","#qn","#VcMins"]
		df = pd.DataFrame(index=days)
		for c in columns:
			df[c] = 0
		

		for datapoint in voice_data:
			day = datapoint['datetime'].date()
			df["#VcMins"][day] += datapoint["length_mins"]


		for datapoint in text_data:
			day = datapoint['datetime'].date()
			
			df['#Messages'][day] += 1

			df['#Characters'][day] += datapoint['length']
			
			if datapoint['qn']:
				df['#qn'][day] += 1
			
			elif datapoint['qj']:
				df['#qj'][day] += 1


		bar_plot(df[["#Characters","#VcMins"]],"g1.png",palette="hls")
		bar_plot(df[["#qn","#qj"]],"g2.png",palette="Set2")

		with open('g1.png','rb') as f:
			with open('g2.png','rb') as f2:
				fs = [discord.File(f,filename='Activity Graph.png'), discord.File(f2,filename='QueueBot Usage Graph.png')]

				await ctx.send("User data for " + member.display_name + ":",files=fs)

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

def bar_plot(df,name,palette = None):
		plt.close("all")
		plt.clf()
		if palette != None:
			sns.set_palette(palette)
		plot = df.plot.bar(subplots=True)

		# plot.set(xticks=days)
		plt.xticks(rotation=90)
		for ax in plot:
			ax.set_title("")
		fig = plot[0].get_figure()


		fig.savefig(name)
	



def voice_state_diff(before,after):
	if before.channel != after.channel:
		if before.self_mute and not after.self_mute:
			return "unmute"
		elif not before.self_mute and after.self_mute:
			return "mute"
		elif before.channel == None or before.afk:
			return f"connected"
		elif after.channel == None:
			return f"disconnected"
		else:
			return f"moved"

def make_naive(dt):
	c = dt
	res = c.astimezone()
	res.replace(tzinfo=None)	
	return res


def setup(bot):
	bot.add_cog(analytics(bot))