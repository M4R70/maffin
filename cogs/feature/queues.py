from discord.ext import commands
import utils.db as db
import discord
import random
from utils.checks import is_host, is_cog_enabled, is_allowed_in_config, dev


async def is_queue_in_channel(ctx):
	q = await db.get_queue(ctx.guild.id, ctx.channel.id)

	if q is None or len(q.keys()) == 1:
		await ctx.send("There is no queue in this channel")
		return False, None
	else:
		return True, q


async def insert_new_queue(ctx, server_id=None, channel_id=None):
	if ctx is not None:
		server_id = ctx.guild.id
		channel_id = ctx.channel.id
		ok, old_queue = await is_queue_in_channel(ctx)
		linked_vc_id = 0
		if ok:
			linked_vc_id = old_queue.get('linked_vc_id',0)
			
	new_queue = {'server_id': server_id, 'channel_id': channel_id, 'locked': False,
				 'order': [], 'open': True, 'closed': False, 'linked_vc_id' : linked_vc_id}
	await db.update_queue(server_id, channel_id, new_queue)


async def get_linked_queue(vc):
	all_queues = await db.get_setting(vc.guild.id, 'existing_queues')
	try:
		del all_queues['_id']
		del all_queues['field_name']
	except KeyError:
		pass

	for queue in all_queues.values():
		if int(queue.get('linked_vc_id', "0")) == vc.id:
			res = queue, vc.guild.get_channel(int(queue['channel_id']))
			if res is not None:
				return res
	return None, None


async def make_queue_embeds(ctx, queue):
	e = discord.Embed()
	embeds = [e]
	e.colour = discord.Colour.blue()
	e.title = "Queue:"
	i = 0
	j = 0
	for guyid in queue['order']:
		try:
			guy = ctx.guild.get_member(int(guyid))
		except ValueError:
			guy = guyid
		if guy:
			try:
				if i + j * 20 == 0:
					embeds[j].add_field(name=f"\u200b \u0009 Current turn: {guy.display_name}", value="\u200b",
										inline=False)
				else:
					embeds[j].add_field(name=f"\u200b \u0009 {i + j * 20} \u200b \u0009 {guy.display_name}",
										value="\u200b",
										inline=False)
			except AttributeError:
				embeds[j].add_field(name=f"\u200b \u0009 {i + j * 20} \u200b \u0009 {guy}", value="\u200b",
									inline=False)

			i += 1
			if i > 20:
				new_embed = discord.Embed()
				new_embed.colour = discord.Colour.blue()
				embeds.append(new_embed)
				j += 1
				i = 1
	pop = False
	for em in embeds:
		if queue['locked']:
			em.set_footer(text="the queue is locked")
		if queue['closed']:
			em.set_footer(text="the queue is closed")
		if len(em.fields) == 0:
			pop = True
	if pop and len(embeds) > 1:
		embeds.pop()
	return embeds





class Queues(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.updating = False

	@commands.Cog.listener()
	async def on_voice_state_update(self, member, before, after):
		if before.channel != after.channel:
			if after.channel is None and before.channel is not None:
				if len(before.channel.members) == 0:
					queue, text_channel = await get_linked_queue(before.channel)
					if text_channel is not None:
						if len(queue['order']) > 0:
							await insert_new_queue(None, channel_id=text_channel.id, server_id=member.guild.id)
							await text_channel.send("Voice channel is empty, resetting queue...")

	@is_allowed_in_config()
	@commands.command()
	async def qcopy(self, ctx, *, source_channel: discord.TextChannel):
		"""Copies the queue from the indicated text channel"""
		source_queue = await db.get_queue(source_channel.guild.id, source_channel.id)
		if source_queue is None:
			await ctx.send("There is no queue in that channel")
			return
		source_queue['channel_id'] = ctx.channel.id
		await db.update_queue(ctx.guild.id, ctx.channel.id, source_queue)
		await ctx.send(f"Copied queue from {source_channel} to {ctx.channel}")

	async def display_queue_update(self, ctx, queue):
		active = queue.get('event')
		if active in [None, False]:
			return
		if self.updating:
			return
		self.updating = True
		display_channel = ctx.guild.get_channel(queue['event']['display_channel'])
		embeds_to_publish = await make_queue_embeds(ctx, queue)
		old_messages_ids = queue['event']['display_messages'][:len(embeds_to_publish)]
		to_delete = queue['event']['display_messages'][len(embeds_to_publish):]

		for id in old_messages_ids:
			try:
				old_message = await display_channel.fetch_message(id)
				e = embeds_to_publish.pop(0)
				await old_message.edit(embed=e)
			except (discord.errors.NotFound, IndexError) as e:
				print(e)
				queue['event']['display_messages'].remove(id)

		for e in embeds_to_publish:
			msg = await display_channel.send(embed=e)
			queue['event']['display_messages'].append(msg.id)

		for id in to_delete:
			try:
				msg = await display_channel.fetch_message(id)
				await msg.delete()
				queue['event']['display_messages'].remove(id)
			except discord.errors.NotFound:
				pass

		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		self.updating = False

	@is_allowed_in_config()
	@commands.command()
	async def qshuffle(self, ctx):
		"""Shuffle the queue!"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return

		random.shuffle(queue['order'])
		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("The queue was shuffled :p")

	@is_allowed_in_config()
	@commands.command()
	async def put(self, ctx, guy1: discord.Member, *, position: int):
		"""Puts the tagged user in the indicated spot"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		try:
			if guy1.id in queue['order']:
				queue['order'].remove(guy1.id)
			queue['order'].insert(position, guy1.id)
			await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
			await ctx.send("Done :thumbsup:")
		except Exception as e:
			print(e)
			await ctx.send("Invalid insert, please use !put <mention> <valid_index>")

	@commands.command()
	@is_allowed_in_config()
	async def qlink(self, ctx):
		"""link the vc you are in to the text channel queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		vc = ctx.author.voice
		if vc is None:
			await ctx.send("Error, you are not connected to a voice channel")
			return
		queue['linked_vc_id'] = vc.channel.id
		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("Linked :thumbsup:")

	@commands.command()
	@is_allowed_in_config()
	async def qcreate(self, ctx):
		"""creates a queue"""
		await insert_new_queue(ctx)
		await ctx.send("Queue Created :thumbsup:")

	@commands.command()
	@is_allowed_in_config()
	async def qdelete(self, ctx):
		"""Deletes the queue"""
		await db.delete_queue(ctx.guild.id, ctx.channel.id)
		await ctx.send("Queue Deleted :thumbsup:")

	@commands.command()
	@is_allowed_in_config()
	async def qreset(self, ctx):
		"""Resets the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		await insert_new_queue(ctx)
		await ctx.send("Queue reset :thumbsup:")

	@commands.command()
	@is_allowed_in_config()
	async def qlock(self, ctx):
		"""Locks the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		queue['locked'] = True

		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("Queue Locked")

	@dev()
	@commands.command()
	# @is_allowed_in_config()
	async def event_display(self, ctx, display_channel: discord.TextChannel = None):
		"""Enable/Disable Event Mode"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return

		e = queue.get('event', {'active': False})
		if e['active'] is False and display_channel is not None:
			e['active'] = True
			e['display_channel'] = display_channel.id
			await ctx.send(f'Queue will be displayed on {display_channel}')
			e['display_messages'] = []
			await self.display_queue_update(ctx,queue)
		else:
			await ctx.send(f'Event display disabled')
		queue['event'] = e
		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)

	@commands.command()
	@is_allowed_in_config()
	async def qunlock(self, ctx):
		"""Unlocks the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		queue['locked'] = False

		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("Queue Unlocked")

	@commands.command()
	@is_allowed_in_config()
	async def qclose(self, ctx):
		"""Close the queue, so that no one can join"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		queue['closed'] = True

		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("Queue closed")

	@commands.command()
	@is_allowed_in_config()
	async def qopen(self, ctx):
		"""open the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		queue['closed'] = False

		await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
		await ctx.send("Queue opened")

	@commands.command(aliases=['qj'])
	async def qjoin(self, ctx):
		"""Adds you to the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		if not queue['closed']:
			if ctx.author.id in queue['order']:
				await ctx.send("You're already in the queue >:v")
			else:
				queue['order'].append(ctx.author.id)
				await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
				await ctx.send(ctx.author.mention + ' joined the queue!')
		else:
			await ctx.send("Sorry, the queue you are trying to join is closed :(")

		await self.display_queue_update(ctx, queue)

	@commands.command(aliases=['ql'])
	async def qleave(self, ctx):
		"""Removes you from the queue """
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		if ctx.author.id in queue['order']:
			queue['order'].remove(ctx.author.id)
			await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
			await ctx.send(ctx.author.mention + ' left the queue :(')
		else:
			await ctx.send("You are not in the queue!")
		await self.display_queue_update(ctx, queue)

	@is_allowed_in_config()
	@commands.command()
	async def shoo(self, ctx, *, guy: discord.Member):
		"""Forcefully remove and user the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		if guy.id in queue['order']:
			queue['order'].remove(guy.id)
			await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
			await ctx.send(guy.display_name + ' was shooed away from the queue :(')
		else:
			await ctx.send(guy.display_name + ' is not in the queue >:v')

		await self.display_queue_update(ctx, queue)

	@commands.command()
	async def qn(self, ctx):
		"""Starts the next turn"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return

		host = await is_host(ctx.guild.id, ctx.author)
		host_in_vc = True
		linked_vc_id = int(queue.get('linked_vc_id','0'))
		linked_vc = ctx.guild.get_channel(linked_vc_id)
		if linked_vc is not None:
			host_in_vc = False
			for user in linked_vc.members:
				is_h = await is_host(ctx.guild.id, user)
				if is_h:
					host_in_vc = True
					break
		if not host_in_vc and queue['locked']:
			await ctx.send("There is no host in vc, auto unlocking queue ...")
			queue['locked'] = False
		if not queue['locked'] or host:
			if len(queue['order']) > 1:
				passed = queue['order'].pop(0)
				now_id = queue['order'][0]
				now = ctx.guild.get_member(now_id)
				while now is None and len(queue['order']) > 0:
					queue['order'].pop(0)
					now_id = queue['order'][0]
					now = ctx.guild.get_member(now_id)
				await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
				try:
					if now.voice.mute:
						await now.edit(mute=False)
						await ctx.send(f"{now.mention} was automatically unmuted because it's his/her turn!")
				except:
					pass
				if len(queue['order']) > 1:
					after = ctx.guild.get_member(queue['order'][1])
					if now is None:
						await ctx.send(f"Queue is empty")
					elif after is None:
						await ctx.send(f"It is now {now.mention}'s turn!")
					else:
						await ctx.send(
							f"It is now {now.mention}'s turn! {after.mention} please be ready, your turn comes afterwards!")
				else:
					await ctx.send(f"It is now {now.mention}'s turn!")

				if linked_vc is not None and not now in linked_vc.members:
					await  ctx.send(f"\nNote: {now} is not on the voice channel")

			else:
				if len(queue['order']) == 1:
					queue['order'].pop(0)
					await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
				await ctx.send("The queue is empty :(")
		else:
			await ctx.send('You are not authorized to do this')

		await self.display_queue_update(ctx, queue)

	@is_allowed_in_config()
	@commands.command()
	async def drag(self, ctx, *, guy: discord.Member):
		"""Forcefully add and user the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		if guy.id in queue['order']:
			await ctx.send(guy.display_name + ' already is in the queue >:v')
		else:
			queue['order'].append(guy.id)
			await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
			await ctx.send(guy.display_name + ' was dragged to the queue!')

		await self.display_queue_update(ctx, queue)

	@dev()
	@commands.command()
	async def test_add(self, ctx, n: int):
		"""test adds dummys to the queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return
		else:
			for i in range(n):
				queue['order'].append(f'dummy {i}')
			await db.update_queue(ctx.guild.id, ctx.channel.id, queue)
			await ctx.send('Done')
			qprint = [c for c in ctx.cog.get_commands() if c.name == 'qprint'][0]
			await ctx.invoke(qprint)

		await self.display_queue_update(ctx, queue)

	@commands.command(aliases=["q"])
	async def qprint(self, ctx):
		"""Prints the current queue"""
		ok, queue = await is_queue_in_channel(ctx)
		if not ok:
			return

		if queue.get('event',{'active':False})['active']:
			await self.display_queue_update(ctx, queue)
			return
		embeds = await make_queue_embeds(ctx, queue)

		for em in embeds:
			await ctx.send(embed=em)
		await self.display_queue_update(ctx, queue)

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res


def setup(bot):
	bot.add_cog(Queues(bot))
