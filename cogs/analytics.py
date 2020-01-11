from discord.ext import commands

import discord
# import asyncio
# import timeago
import datetime
import timedelta
import utils.db
from utils.checks import dev
import seaborn as sns
from matplotlib import pyplot as plt
import pandas as pd
import timeago

class analytics(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.converter = commands.MemberConverter()
		self.dynamic_connection_data = {}

	def validate_settings(self, settings, guild):
		try:
			if settings["enabled"]:
				pass
		except KeyError as e:
			return f"logs, Missing field {e}"

		return True

	# moved, disconnected, connected

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		settings = await self.bot.cogs["Settings"].get(member.guild.id, "logs")
		if not settings['enabled']:
			return

		action = voice_state_diff(before, after)

		now = datetime.datetime.now()
		if action == "connected":
			await self.log_connection(member, now)
		elif action == "disconnected":
			await self.log_disconnection(member, before.channel, now)
		elif action == "move":
			await self.log_disconnection(member, before.channel, now)
			await self.log_connection(member, now)

	async def log_connection(self, member, now):
		try:
			self.dynamic_connection_data[member.guild.id][member.id] = now
		except KeyError:
			self.dynamic_connection_data[member.guild.id] = {}
			self.dynamic_connection_data[member.guild.id][member.id] = now

	async def log_disconnection(self, member, channel, now):
		try:
			start = self.dynamic_connection_data[member.guild.id][member.id]
			del self.dynamic_connection_data[member.guild.id][member.id]
		except KeyError:
			return

		connection_time = now - start

		d = {
			"member_id": member.id,
			"voice_channel id": channel.id,
			"guild_id": member.guild.id,
			"length_mins": connection_time.total_seconds() / 60,
			"datetime": now
		}

		await utils.db.insertOne(f"analytics.voice.a{member.guild.id}", d)





	@dev()  # temp!
	@commands.command()
	async def pull_text_data_from_api(self, ctx, n = 5):
		today = datetime.datetime.now()
		last_day = today - timedelta.Timedelta(days=n)

		this_marker = {
			"from":today,
			"to":last_day,
			"id":ctx.message.id,
		}

		query_periods = [this_marker]


		query = {
			"from": {
				"$gte": last_day
				}
		}		

		cache_markers = await utils.db.find(f"analytics.text.a{ctx.guild.id}.cache_markers", query)


		for marker in cache_markers:
			query_periods = insert_marker(marker,query_periods)
		
		def to_string(m):
			now = datetime.datetime.now()
			return f"From {(now - m['from']).days} days go, To : {(now - m['to']).days} days go"


		total_query_days = 0
		for period in query_periods:
			total_query_days += (period["from"] - period["to"]).days

		newline = '\n'

		await ctx.send( f"Periods to query:  {newline}{newline.join([to_string(p) for p in query_periods ])}" + '\n' + f"total: {total_query_days} days")


		count = 0
		for period in query_periods:
			for channel in ctx.guild.text_channels:
				try:
					async for message in channel.history(limit=None,after=period["to"],before=period["from"]):
						await self._log_message(message)
						count += 1
				except Exception as e:
					print(e)

		for marker in cache_markers:
			await utils.db.deleteOne(f"analytics.text.a{ctx.guild.id}.cache_markers",marker)
		
		await utils.db.insertOne(f"analytics.text.a{ctx.guild.id}.cache_markers",this_marker)

		await ctx.send(f"Cached {count} messages :thumbsup:")


	@dev()  # temp!
	@commands.command()
	async def insert_test_marker(self, ctx, n_from:int, n_to:int):
		fom = datetime.datetime.now() - timedelta.Timedelta(days= n_from)
		to = datetime.datetime.now() - timedelta.Timedelta(days= n_to)
		

		await utils.db.insertOne(f"analytics.text.a{ctx.guild.id}.cache_markers", {"to":to,"from":fom})



	async def _log_message(self,message):

		settings = await self.bot.cogs["Settings"].get(message.guild.id, "analytics")
		if not settings['enabled']:
			return

		data = {
			"member_id": message.author.id,
			"text_channel_id": message.channel.id,
			"guild_id": message.guild.id,
			"length": len(message.content),
			"datetime": datetime.datetime.now(),
			"qj": False,
			"qn": False,
			"message_id": message.id
		}

		if message.content == "!qj":
			data["qj"] = True
		elif message.content == "!qn":
			data["qn"] = True

		await utils.db.updateOne(f"analytics.text.a{message.guild.id}",{"message_id":message.id}, {"$set":data})

	@commands.Cog.listener()
	async def on_message(self, message):
		await self._log_message(message)



	@dev()  # temp!
	@commands.command()
	async def info(self, ctx, *args):

		n, member = await self.parse_params(ctx, args)

		now = datetime.datetime.now()

		query = {
			"datetime": {
				"$lt": now,
				"$gte": now - timedelta.Timedelta(days=n)
			},
			"member_id": member.id,
			"guild_id": member.guild.id
		}

		text_data = await utils.db.find(f"analytics.text.a{member.guild.id}", query)
		voice_data = await utils.db.find(f"analytics.voice.a{member.guild.id}", query)

		days = [now.date()]

		for i in range(1, n + 1):
			days.append((now - timedelta.Timedelta(days=i)).date())

		days = list(reversed(days))

		columns = ['#Messages', '#Characters', "#qj", "#qn", "#VcMins"]
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

		bar_plot(df[["#Characters", "#VcMins"]], "g1.png", palette="hls")
		bar_plot(df[["#qn", "#qj"]], "g2.png", palette="Set2")

		with open('g1.png', 'rb') as f:
			with open('g2.png', 'rb') as f2:
				fs = [discord.File(f, filename='Activity Graph.png'),
					  discord.File(f2, filename='QueueBot Usage Graph.png')]

				await ctx.send("User data for " + member.display_name + ":", files=fs)

	async def parse_params(self, ctx, args):
		n = None
		member = None
		for a in args:
			if member == None:
				try:
					member = await self.converter.convert(ctx, a)
					continue
				except discord.ext.commands.errors.BadArgument as e:
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

		return n, member


def insert_marker(marker,periods):

	def es_antes(d1,d2):
		return d1 > d2


	for i in range(len(periods)):
		period = periods[i]

		if es_antes(period["from"],marker["from"]) and es_antes(marker["to"],period["to"]):
				periods.insert(i+1,{"from":marker["to"], "to": period["to"] })
				periods[i]["to"] = marker["from"]
				return periods

		elif es_antes(period["from"],marker["from"]) and es_antes(period["to"],marker["to"]):
			continue
		
		
		else:
			print("DAFUQ?! analytics.py:insert_marker")
		
					

def bar_plot(df, name, palette=None):
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


def voice_state_diff(before, after):
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
