from collections import defaultdict
from discord.ext import commands
import discord
from utils import db
from utils.checks import is_cog_enabled,dev
import pandas as pd
import seaborn as sns
import pytz
import matplotlib.pyplot as plt
import datetime
from utils.misc import convert_member, convert_int
import timeago


def aware(d):
	return d.tzinfo is not None and d.tzinfo.utcoffset(d) is not None


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


def parse_voice_mins(raw_voice_df):
	raw_voice_df['datetime'] = raw_voice_df['_id'].apply(
		lambda x: x.generation_time.replace(tzinfo=pytz.timezone('UTC')))
	raw_voice_df = raw_voice_df.copy()
	per_user = raw_voice_df.groupby('member_id')
	vc_mins_df = pd.DataFrame()
	for label, user_df in per_user:
		user_df = user_df.sort_values(by='datetime')
		conn_row = None
		for index, row in user_df.iterrows():
			if conn_row is None and row['event'] == 'connected':
				conn_row = row
			elif conn_row is not None and row['event'] == 'disconnected':
				delta = row['datetime'] - conn_row['datetime']
				len = int(delta.total_seconds() / 60)
				try:
					vc_mins_df = vc_mins_df.append(
						{'member_id': row['member_id'], 'delta': delta, 'datetime': conn_row['datetime'],
						 'len': len},
						ignore_index=True)
				except Exception as e:
					print(e)
				# print(int(delta.total_seconds()/60))
				conn_row = None

	return vc_mins_df


def sum_dayly_barchart(df, n, x='datetime', y='len', fname='sum_dayly_barchart.png', m=None):
	df = df.copy()
	grouped_df = df.groupby(pd.Grouper(key=x, freq=f'1D'))[y].agg('sum')
	grouped_df = grouped_df.reset_index()
	grouped_df['aux'] = grouped_df[x].apply(lambda d: d.strftime("%d %b"))
	inactive_days = grouped_df[grouped_df['len'] == 0]
	low_activity_days = grouped_df[grouped_df['len'] < 30]
	low_activity_days = low_activity_days[low_activity_days['len'] > 0]

	sns.barplot(data=grouped_df, x='aux', y=y)
	plt.xticks(rotation=90)

	if 'delta' not in df.columns:
		subject = "Text Characters Sent"
		ylabel = 'Characters'
	else:
		subject = "Voice Chat Minutes"
		ylabel = 'Minutes'
	user = 'Member: ' + m.display_name if m is not None else "Whole Server"
	plt.title(f'Total {subject} Per Day (last {n} days) \n For {user}')
	plt.ylabel(f'{ylabel}')
	plt.xlabel('day')
	plt.savefig(fname)
	plt.clf()
	return fname, inactive_days, low_activity_days


def avg_weekly_hourly(df, n, x='datetime', y='len', fname="avg_weekly_hourly.png", m=None):
	df = df.copy()
	df['weekday'] = df[x].apply(lambda x: x.strftime("%A"))
	df['hour'] = df[x].apply(lambda x: x.strftime("%H"))
	grouped_df = df.groupby(['weekday', 'hour'])[y].mean()
	grouped_df = grouped_df.reset_index()
	# plt.figure(figsize=(10, 5))
	palette = sns.color_palette()
	i = 0
	for weekday in set(grouped_df['weekday']):
		w_df = grouped_df[grouped_df['weekday'] == weekday]

		for j in range(25):
			j = str(j).zfill(2)
			if len(w_df[w_df['hour'] == j]) == 0:
				w_df = w_df.append({'weekday': weekday, 'hour': j, y: 0}, ignore_index=True)
		w_df['hour'] = w_df['hour'].astype(int)
		w_df.sort_values(by=['hour'], inplace=True)

		plt.plot(w_df['hour'], w_df[y], 'o-', label=weekday)
		i += 1

	plt.xticks(rotation=90)
	plt.legend()
	if 'delta' not in df.columns:
		subject = "Text Characters Sent"
		ylabel = 'Characters'
	else:
		subject = "Voice Chat Minutes"
		ylabel = 'Minutes'

	user = 'Member: ' + m.display_name if m is not None else "Whole Server"
	plt.title(f'Avg {subject} Per Hour (UTC timezone) (last {n} days) \n For {user}')
	plt.ylabel(ylabel)
	plt.xlabel('Hour (UTC)')
	plt.savefig(fname)
	plt.clf()
	return fname


def avg_hourly(df, n, x='datetime', y='len', fname="avg_hourly.png", m=None):
	df = df.copy()
	first_day = max(df[x])
	tresh = first_day - datetime.timedelta(days=n)
	df = df[df[x] > tresh]
	df['hour'] = df[x].apply(lambda x: x.strftime("%H"))
	grouped_df = df.groupby(['hour'])[y].mean()
	grouped_df = grouped_df.reset_index()
	plt.figure(figsize=(10, 5))
	for j in range(25):
		j = str(j).zfill(2)
		if len(grouped_df[grouped_df['hour'] == j]) == 0:
			grouped_df = grouped_df.append({'hour': j, y: 0}, ignore_index=True)
	sns.barplot(data=grouped_df, x='hour', y=y)
	plt.xticks(rotation=90)
	if 'delta' not in df.columns:
		subject = "Text Characters Sent"
		ylabel = 'Characters'
	else:
		subject = "Voice Chat Minutes"
		ylabel = 'Minutes'
	user = 'Member: ' + m.display_name if m is not None else "Whole Server"
	plt.title(f'Avg {subject} Per Hour (UTC timezone) (last {n} days)  \n For {user}')
	plt.ylabel(ylabel)
	plt.xlabel('Hour (UTC)')
	plt.savefig(fname)
	plt.clf()
	return fname


async def parse_args(args, ctx):
	member = None
	n = None
	level = None
	for a in args:
		print(a)
		if member is None:
			member = await convert_member(ctx, a)
		if n is None:
			n = convert_int(a)
		print('b')
		if level is None:
			if a in ['basic', 'mid', 'full']:
				print('a')
				level = a
	if n is None:
		n = 30
	if member is not None:
		query = {'member_id': member.id}
	else:
		query = {}
	if level is None:
		level = 'mid'
	return member, n, query, level


class Analytics(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@dev()
	@commands.command()
	async def gimme_csv(self, ctx, *args):
		voice_data = await db.get(ctx.guild.id, 'analytics.voice', {}, list=True)
		df = pd.DataFrame(voice_data)
		df.to_csv('voice.csv')

	# @commands.command()
	# async def to_member(self, ctx, *args):
	# 	all_data = await db.get(ctx.guild.id, 'analytics.text', {}, list=True)
	# 	for d in all_data:
	# 		try:
	# 			d['member_id'] = d['author_id']
	# 			del d['author_id']
	# 			await db.update(ctx.guild.id, 'analytics.text', d)
	# 			print('yes')
	# 		except KeyError:
	# 			print('shit')
	# 	print('done')
	@dev()
	@commands.command()
	async def howmany(self, ctx, r:discord.Role):
		"""Returns how many members have the specified role"""
		await ctx.send(f"There's {len(r.members)} members with the {r.name} role")

	@dev()
	@commands.command()
	async def stats(self, ctx, *args):
		"""!stats <member=None> <n_days=30> <low/mid/full>"""
		msg = await ctx.send('processing....')
		member, n, query, level = await parse_args(args, ctx)
		e = None
		print(level)
		text_data = await db.get(ctx.guild.id, 'analytics.text', query, list=True)
		voice_data = await db.get(ctx.guild.id, 'analytics.voice', query, list=True)

		text_df = pd.DataFrame(text_data)
		text_df['datetime'] = text_df['_id'].apply(lambda x: x.generation_time.replace(tzinfo=pytz.timezone('UTC')))
		raw_voice_df = pd.DataFrame(voice_data)
		voice_df = parse_voice_mins(raw_voice_df)
		dfs = [text_df, voice_df]

		today = datetime.datetime.utcnow().replace(tzinfo=pytz.timezone('UTC'))
		first_day_in_graph = today - datetime.timedelta(days=n - 1)

		files = []

		if member is not None:
			e = discord.Embed()
			e.title = f"Stats for {member.display_name} for the last {n} days"
			e.add_field(name='Joined', value=timeago.format(member.joined_at, datetime.datetime.utcnow()))

		i = 0
		df_name = 'text'
		for df in dfs:
			df['len'] = df['len'].astype(int)
			# df['datetime'] = df['datetime'].astype('datetime64[ns]')
			df = df[df['datetime'] > first_day_in_graph]
			df = df[df['datetime'] <= today]
			df = df.append({'len': 0, 'datetime': first_day_in_graph}, ignore_index=True)
			df = df.append({'len': 0, 'datetime': today}, ignore_index=True)
			fname, inactive, low = sum_dayly_barchart(df, n, m=member, fname=str(i) + '.png')

			if member is not None:
				if df_name == 'text':
					e.add_field(name="\u200b", value="\u200b", inline=False)
					e.add_field(name=f"Text chars sent", value=f"{df['len'].sum()}")

					e.add_field(name=
								"Text Inactive days", value=f"{len(inactive)}/{n}")
					e.add_field(name=
								"Text low activity days", value=f"{len(low)}/{n}")
					e.add_field(name ="\u200b",value="\u200b",inline=False)


				else:
					e.add_field(name=f"VC mins ", value=f"{df['len'].sum()}")
					e.add_field(name=
								"Voice Inactive days", value=f"{len(inactive)}/{n}")
					e.add_field(name=
								"Voice low activity days", value=f"{len(low)}/{n}")

			if level in ['mid', 'full']:
				files.append(fname)
				i += 1
			if level == 'full':
				files.append(avg_weekly_hourly(df, n, m=member, fname=str(i) + '.png'))
				i += 1
				files.append(avg_hourly(df, n, m=member, fname=str(i) + '.png'))
				i += 1
			df_name = 'voice'

		print('graphed')
		files = [discord.File(x) for x in files]
		await ctx.send("\u200b", embed=e, files=files)
		await msg.delete()
		plt.close('all')
		print('sent')

	@commands.Cog.listener()
	async def on_message(self, message):
		enabled = await is_cog_enabled(None, message.guild.id, 'analytics')
		if enabled:
			doc = {'message_id': message.id, 'channel_id': message.channel.id, 'len': len(message.content),
				   'member_id': message.author.id}
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
