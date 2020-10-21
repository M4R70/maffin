from collections import defaultdict
from discord.ext import commands
import discord
from utils import db
from utils.checks import is_cog_enabled
import pandas as pd
import seaborn as sns
import pytz
import matplotlib.pyplot as plt
import datetime


def voice_state_diff(before, after):
	if before.channel != after.channel:
		if before.channel is None or before.afk and after.channel is not None:
			return f"connected"
		elif after.channel is None and before.channel is not None:
			return f"disconnected"
		elif before.channel is not None and after.channel is not None:
			return f"moved"
	else:
		return None


def sum_dayly_barchart(df, n, x='datetime', y='len', fname='sum_dayly_barchart.png'):
	first_day = max(df[x])
	tresh = first_day - datetime.timedelta(days=n)
	df = df[df[x] > tresh]
	grouped_df = df.groupby(pd.Grouper(key=x, freq=f'1D'))[y].agg('sum')
	grouped_df = grouped_df.reset_index()
	grouped_df['aux'] = grouped_df[x].apply(lambda d: d.strftime("%d %b"))
	plt.figure(figsize=(n / 3, 5))
	sns.barplot(data=grouped_df, x='aux', y=y)
	plt.xticks(rotation=90)
	if y == 'len':
		plt.title(f'Total Text Characters Sent Per Day (last {n} days) ')
		plt.ylabel('Characters')
	plt.xlabel('day')
	plt.savefig(fname)
	plt.clf()


def avg_weekly_hourly(df, n, x='datetime', y='len', fname="avg_weekly_hourly.png"):
	df = df.copy()
	first_day = max(df[x])
	tresh = first_day - datetime.timedelta(days=n)
	df = df[df[x] > tresh]
	df['weekday'] = df[x].apply(lambda x: x.strftime("%A"))
	df['hour'] = df[x].apply(lambda x: x.strftime("%H"))
	grouped_df = df.groupby(['weekday', 'hour'])[y].mean()
	grouped_df = grouped_df.reset_index()
	# plt.figure(figsize=(10, 5))
	palette = sns.color_palette()
	i = 0
	for weekday in set(grouped_df['weekday']):
		w_df = grouped_df[grouped_df['weekday'] == weekday]
		#sns.scatterplot(data=w_df, x='hour', y=y, label=weekday,linewidth=3,color=palette[i])
		plt.plot(w_df['hour'],w_df[y],'o-',label=weekday)
		i+=1
	plt.xticks(rotation=90)
	plt.legend()
	if y == 'len':
		plt.title(f'Avg Text Characters Sent Per Hour (UTC timezone) (last {n} days)')
		plt.ylabel('Avg Characters')
	plt.xlabel('Hour (UTC)')
	plt.savefig(fname)
	plt.clf()


def avg_hourly(df, n, x='datetime', y='len', fname="avg_hourly.png"):
	df = df.copy()
	first_day = max(df[x])
	tresh = first_day - datetime.timedelta(days=n)
	df = df[df[x] > tresh]
	df['hour'] = df[x].apply(lambda x: x.strftime("%H"))
	grouped_df = df.groupby(['hour'])[y].mean()
	grouped_df = grouped_df.reset_index()
	plt.figure(figsize=(10, 5))
	sns.barplot(data=grouped_df, x='hour', y=y)
	plt.xticks(rotation=90)
	if y == 'len':
		plt.title(f'Avg Text Characters Sent Per Hour (UTC timezone) (last {n} days)')
		plt.ylabel('Avg Characters')
	plt.xlabel('Hour (UTC)')
	plt.savefig(fname)
	plt.clf()


class Analytics(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def insights(self, ctx, member: discord.Member = None, n: int = 30):
		if member is not None:
			query = {'author_id': member.id}
		else:
			query = {}
		text_data = await db.get(ctx.guild.id, 'analytics.text', query, list=True)
		print(f"len(text_data) = {len(text_data)}")
		df = pd.DataFrame(text_data)
		df['datetime'] = df['_id'].apply(lambda x: x.generation_time.replace(tzinfo=pytz.timezone('UTC')))
		df['len'] = df['len'].astype(int)
		df['datetime'] = df['datetime'].astype('datetime64[ns]')

		sum_dayly_barchart(df, n)
		avg_weekly_hourly(df, n)
		avg_hourly(df, n)
		print('graphed')
		files = [discord.File(x + '.png') for x in ['sum_dayly_barchart', 'avg_weekly_hourly', 'avg_hourly']]
		await ctx.send(files=files)
		plt.close('all')

		print('sent')

	@commands.Cog.listener()
	async def on_message(self, message):
		enabled = await is_cog_enabled(None, message.guild.id, 'analytics')
		if enabled:
			doc = {'message_id': message.id, 'channel_id': message.channel.id, 'len': len(message.content),
				   'author_id': message.author.id}
			await db.insert(message.guild.id, 'analytics.text', doc)

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):

		enabled = await is_cog_enabled(None, member.guild.id, 'analytics')
		if not enabled:
			return

		diff = voice_state_diff(before, after)
		if diff is None:
			return

		doc = {'member_id': member.id, 'event': diff}
		if diff == "connected":
			doc['channel_id'] = after.channel.id
		elif diff == "disconnected":
			doc['channel_id'] = before.channel.id
		elif diff == "moved":
			doc['before_channel_id'] = before.channel.id
			doc['after_channel_id'] = after.channel.id
		await db.insert(member.guild.id, 'analytics.voice', doc)

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(Analytics(bot))
