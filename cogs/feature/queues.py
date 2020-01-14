from discord.ext import commands
import utils.db
import discord
import random


async def queue_exists(ctx):
	q = await utils.db.findOne('queues', {'channel_id': ctx.channel.id, 'guild_id': ctx.guild.id})
	if q == None:
		return False
	else:
		return True


async def enabled(ctx):
	s = await utils.db.findOne("settings", {'guild_id': ctx.guild.id})
	if s['queues']['enabled']:
		return True
	else:
		return False


async def host(ctx):
	s = await utils.db.findOne("settings", {'guild_id': ctx.guild.id})
	role_ids = s['queues']['host_role_ids']
	hostRoles = [r for r in ctx.guild.roles if r.id in role_ids]
	if not set(hostRoles).isdisjoint(ctx.author.roles):
		return True
	else:
		return False


class queues(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	def validate_settings(self, settings, guild):
		try:
			print(settings)
			if settings["enabled"]:
				hostRoles = [r for r in guild.roles if r.id in settings['host_role_ids']]
				if len(hostRoles) == 0:
					return "Queues: host role(s) not found"
		except KeyError as e:
			return f"Queues, Missing field {e}"

		return True

	@commands.has_permissions(administrator=True)
	@commands.command()
	async def qcreate(self, ctx):

		passes_checks, msg = await check(ctx,["enabled"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		q = await get_queue(ctx.channel.id)
		if q is None:
			await utils.db.insertOne('queues',
									 {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id, 'moderated': True,
									  'order': [], 'open': True})
			await ctx.send("Queue created :thumbsup:")
		else:
			await ctx.send('This channel already has a queue!')

	@commands.has_permissions(administrator=True)
	@commands.command()
	async def qdelete(self, ctx):

		passes_checks, msg = await check(ctx,["enabled","exists"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		await utils.db.deleteOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id})
		await ctx.send("Queue deleted :thumbsup:")


	@commands.command()
	async def shuffle(self, ctx):

		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		q = await get_order(ctx.channel.id)
		random.shuffle(q)
		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {"order": q}})
		await ctx.send("Queue shuffled :thumbsup:")
		await _qprint(ctx)

	@commands.command()
	async def qreset(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {"order": [], "open": True}})
		await ctx.send("Queue cleared :thumbsup:")

	@commands.command()
	async def qunlock(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {"moderated": False}})
		await ctx.send("This queue is now unlocked :thumbsup:")

	@commands.command()
	async def qlock(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {"moderated": True}})
		await ctx.send("This queue is now locked :thumbsup:")

	@commands.command(aliases=['qj'])
	async def qjoin(self, ctx):
		passes_checks, msg = await check(ctx,["enabled", "exists"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		queue = await get_queue(ctx.channel.id)
		if queue['open']:
			q = queue['order']
			if ctx.author.id in q:
				await ctx.send("You're already in the queue >:v")
			else:
				q.append(ctx.author.id)
				await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
										 {'$set': {'order': q}})
				await ctx.send(ctx.author.mention + ' joined the queue!')
		else:
			await ctx.send("Sorry, the queue you are trying to join is closed :(")

	@commands.command(aliases=['ql'])
	async def qleave(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		q = await get_order(ctx.channel.id)
		if ctx.author.id in q:
			q.remove(ctx.author.id)
			await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
									 {'$set': {'order': q}})
			await ctx.send(ctx.author.mention + ' left the queue :(')
		else:
			await ctx.send("You are not in the queue!")

	@commands.command()
	async def shoo(self, ctx, *, guy: discord.Member):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		q = await get_order(ctx.channel.id)
		if guy.id in q:
			q.remove(guy.id)
			await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
									 {'$set': {'order': q}})
			await ctx.send(guy.display_name + ' was shooed from the queue :(')
		else:
			await ctx.send(guy.display_name + ' is not in the queue >:v')

	@commands.command()
	async def drag(self, ctx, *, guy: discord.Member):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		q = await get_order(ctx.channel.id)
		if guy.id in q:
			await ctx.send(guy.display_name + ' already is in the queue >:v')
		else:
			q.append(guy.id)
			await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
									 {'$set': {'order': q}})
			await ctx.send(guy.display_name + ' was dragged to the queue!')

	@commands.command()
	async def swap(self, ctx, guy1: discord.Member, *, guy2: discord.Member):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		q = await get_order(ctx.channel.id)
		if guy1.id in q and guy2.id in q:
			i1 = q.index(guy1.id)
			i2 = q.index(guy2.id)
			sq[i1], q[i2] = q[i2], q[i1]
			await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
									 {'$set': {'order': q}})
			await ctx.send(guy1.display_name + " and " + guy2.display_name + " were swapped in the queue!")
		else:
			await ctx.send("Error, please mention two people who are in the queue")

	@commands.command()
	async def put(self, ctx, guy1: discord.Member, *, position: int):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		q = await get_order(ctx.channel.id)
		try:
			if guy1.id in q:
				q.remove(guy1.id)
			q.insert(position, guy1.id)
			await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
									 {'$set': {'order': q}})
			await ctx.send("Done :thumbsup:")
		except Exception as e:
			print(e)
			await ctx.send("Invalid insert, please use !put <mention> <valid_index>")

	@commands.command()
	async def qn(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		is_host = await host(ctx)
		queue = await get_queue(ctx.channel.id)

		if not queue['moderated'] or is_host:
			q = queue['order']
			if len(q) > 0:
				q.remove(q[0])
				now = None
				while now == None:
					now = ctx.guild.get_member(q[0])
					if now == None:
						q.remove(q[0])

				await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
										 {'$set': {'order': q}})
				try:
					if now.voice.mute:
						await now.edit(mute=False)
						await ctx.send(f"{now.mention} was automatically unmuted because it's his/her turn!")
				except:
					pass

				if len(q) > 1:
					after = ctx.guild.get_member(q[1])
					if after == None:
						await ctx.send(f"It is now {now.mention}'s turn!")
					else:
						await ctx.send(
							f"It is now {now.mention}'s turn! {after.mention} please be ready, your turn comes afterwards!")
				else:
					await ctx.send(f"It is now {now.mention}'s turn!")
			else:
				await ctx.send("The queue is empty :(")
		else:
			await ctx.send('You are not authorized to do this')

	@commands.command()
	async def qclose(self, ctx):
		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return

		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {'open': False}})
		await ctx.send("Queue is now closed")


	@commands.command()
	async def qopen(self, ctx):

		passes_checks, msg = await check(ctx,["enabled","exists","host"])
		if not passes_checks:
			if msg is not None:
				await ctx.send(msg)
			return
		await utils.db.updateOne('queues', {'guild_id': ctx.guild.id, 'channel_id': ctx.channel.id},
								 {'$set': {'open': True}})
		await ctx.send("Queue is now open")

	@commands.command(aliases=['q'])
	async def qprint(self, ctx):

		queue_does_exist = await queue_exists(ctx)
		if not queue_does_exist:
			return
		await _qprint(ctx)


async def check(ctx, l):

	if "enabled" in l:
		is_enabled = await enabled(ctx)
		if not is_enabled:
			return False, None

	if "exists" in l:
		queue_does_exist = await queue_exists(ctx)
		if not queue_does_exist:
			return False, "There is no queue in this channel!"

	if "host" in l:
		is_host = await host(ctx)
		if not is_host:
			return False, "You are not authorized to do this"

	return True, "All Passed :thumbsup:"



async def _qprint(ctx):
	q = await get_order(ctx.channel.id)
	e = discord.Embed()
	e.colour = discord.Colour.blue()
	e.title = "Queue:"
	i = 0
	for guyid in q:
		guy = ctx.guild.get_member(guyid)
		if guy:
			if i == 0:
				e.add_field(name=f"\u200b \u0009 Current turn: {guy.display_name}", value="\u200b", inline=False)
			else:
				e.add_field(name=f"\u200b \u0009 {i} \u200b \u0009 {guy.display_name}", value="\u200b", inline=False)

			i += 1
	await ctx.send(embed=e)


async def get_order(channelid):
	q = await get_queue(channelid)
	return q['order']


async def get_queue(channelid):
	q = await utils.db.findOne('queues', {'channel_id': channelid})
	return q


# async def is_host(ctx):
# 	s = await utils.db.findOne("settings", {'guild_id': ctx.guild.id})
# 	role_ids = s['queues']['host_role_ids']
# 	hostRoles = [r for r in ctx.guild.roles if r.id in role_ids]
# 	if not set(hostRoles).isdisjoint(ctx.author.roles):
# 		return True
# 	else:
# 		return False


def setup(bot):
	bot.add_cog(queues(bot))
