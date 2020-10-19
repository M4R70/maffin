from discord.ext import commands
import discord
import utils.db as db
from utils.checks import dev
import asyncio
from collections import defaultdict

emojis = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣',
		  '🔟', '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮',
		  '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸',
		  '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']  # no se ven en pycharm pero hay emojis 1-10 a-z


def make_message(category_data, all_guild_roles):
	msg = '\u200b\n' + category_data['readable_name'] + ':\n'
	used_emojis = {}
	for i in range(category_data['bottom_separator_index'] + 1, category_data['top_separator_index']):
		r = all_guild_roles[i]
		emoji = emojis[i - category_data['bottom_separator_index'] - 1]
		msg += ':small_blue_diamond:  ' + emoji + ' ' + fake_mention(r) + '\n'
		used_emojis[emoji] = r.id
	category_data['used_emojis'] = used_emojis

	return msg, category_data


def fake_mention(role):
	return f"<@&{role.id}>"


#
#
# async def fix_category_indices(guild):
# 	db_info = await db.get_setting(guild.id, 'reactionRoles')
# 	# prefixes = {cat['groupPrefix']:msg_id for msg_id,cat in db_info.items() if msg_id not in ['_id','field_name']}
# 	db_info = {k:v for k,v in db_info.items() if isinstance(v,dict)}
# 	prefixes = {x['groupPrefix'] for x in db_info.values()}
#
# 	for i in range(len(guild.roles)):  # abajo para arriba
# 		r = guild.roles[i]
# 		for groupPrefix in prefixes:
# 			if r.name.startswith('</' + groupPrefix):
# 				for j in range(r.position, len(guild.roles)):
# 					if guild.roles[j].name.startswith('<' + groupPrefix):
# 						for msg_id,cat in db_info.items():
# 							if cat['groupPrefix'] == groupPrefix:
# 								readable_name = r.name[len(groupPrefix) + 2:-1]
# 								if readable_name.endswith('_ex'):
# 									readable_name = readable_name[:-3]
# 								readable_name = readable_name.strip()
# 								if readable_name == cat['readable_name']:
# 									category = cat
#
# 									print(f"{category['readable_name' ]} {category['top_separator_index']}  {category['bottom_separator_index']}")
# 									category["top_separator_index"] = j
# 									category["bottom_separator_index"] = i
# 									#print(db_info[msg_id])
#
# 									await db.update_setting(guild.id, 'reactionRoles',
# 															{"$set": {str(msg_id): category}})
# 									break

def fix_separator_indexes(category, guild):
	bottom = guild.get_role(int(category['bottom_separator_id']))
	if bottom is not None:
		category['bottom_separator_index'] = bottom.position
	top = guild.get_role(int(category['top_separator_id']))
	if top is not None:
		category['top_separator_index'] = top.position

	return category


class ReactionRoles(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.updating = defaultdict(lambda: {})

	@dev()
	@commands.command()
	async def post_rr_group(self, ctx, groupPrefix: str, flag=None):
		"""Post a group of reaction role categories"""

		db_info = await db.get_setting(ctx.guild.id, 'reactionRoles')
		ids = list(db_info.keys())
		ids = [x for x in ids if x not in ['_id', 'field_name']]
		to_unset = []
		for msg_id in ids:
			channel = ctx.guild.get_channel(int(db_info[msg_id]['channel_id']))
			if channel is None:
				to_unset.append(msg_id)
			else:
				try:
					await channel.fetch_message(int(msg_id))
				except discord.errors.NotFound:
					to_unset.append(msg_id)
			for x in to_unset:
				if x not in ["_id", 'field_name']:
					print(x)
					await db.update_setting(ctx.guild.id, 'reactionRoles', {"$unset": {x: 1}})

		first = True
		bot_user = ctx.guild.get_member(self.bot.user.id)
		if bot_user.guild_permissions.mention_everyone and flag != "-f":
			await ctx.send('remove mention everyone permission from bot or use -f flag')
			return
		categories = []
		roles = ctx.guild.roles
		for i in range(len(roles)):  # abajo para arriba
			r = roles[i]
			if r.name.startswith('</' + groupPrefix):
				category_data = {}
				for j in range(r.position, len(roles)):
					if roles[j].name.startswith('<' + groupPrefix):
						category_data["top_separator_index"] = j
						category_data["bottom_separator_index"] = i
						category_data['exclusive'] = False
						category_data['groupPrefix'] = groupPrefix
						category_data['channel_id'] = ctx.channel.id
						category_data['bottom_separator_id'] = roles[i].id
						category_data['top_separator_id'] = roles[j].id
						readable_name = r.name[len(groupPrefix) + 2:-1]

						if readable_name.endswith('_ex'):
							readable_name = readable_name[:-3]
							category_data['exclusive'] = True

						readable_name = readable_name.strip()
						category_data['readable_name'] = readable_name
						categories.append(category_data)
						txt, category_data = make_message(category_data, roles)
						used_emojis = category_data['used_emojis']
						if first:
							txt = txt[2:]
							first = False
						message = await ctx.send(txt)

						for e in emojis:
							if e in used_emojis.keys():
								await message.add_reaction(e)
							else:
								break

						break
				await db.update_setting(ctx.guild.id, 'reactionRoles',
										{"$set": {str(message.id): category_data}})

	@commands.Cog.listener()
	async def on_guild_role_update(self, before, after):

		guild = before.guild
		old_cat_fixed = False
		new_cat_fixed = False
		if before.position != after.position:
			# await fix_category_indices(guild)
			db_info = await db.get_setting(guild.id, 'reactionRoles')
			del db_info['_id']
			del db_info['field_name']
			for message_id, category in db_info.items():
				before_in_cat = category['bottom_separator_index'] <= before.position <= category['top_separator_index']
				after_in_cat = category['bottom_separator_index'] <= after.position <= category['top_separator_index']
				# print(
				# 	f"{category['readable_name']} {category['bottom_separator_index']} {before.position} {after.position} {category['top_separator_index']}")
				if after_in_cat:
					new_cat_fixed = True
					await self.fix_message(category, guild, message_id)
				elif before_in_cat:
					old_cat_fixed = True
					await self.fix_message(category, guild, message_id)
				if old_cat_fixed and new_cat_fixed:
					break

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		guild, channel, message, user, emoji = await self.parse_payload(payload)
		if user.id == self.bot.user.id:
			return
		db_info = await db.get_setting(guild.id, 'reactionRoles')
		db_info = db_info.get(str(message.id))

		if db_info is None:
			return
		try:
			role_id = int(db_info['used_emojis'][emoji])
		except KeyError:
			return
		role = guild.get_role(role_id)
		if db_info['exclusive']:
			for r_emoji, role_id in db_info['used_emojis'].items():
				if r_emoji != emoji:
					await message.remove_reaction(r_emoji, user)
					r = guild.get_role(role_id)
					await user.remove_roles(r)
		await user.add_roles(role)

	@commands.Cog.listener()
	async def on_raw_reaction_remove(self, payload):

		guild, channel, message, user, emoji = await self.parse_payload(payload)

		if user.id == self.bot.user.id:
			return

		db_info = await db.get_setting(guild.id, 'reactionRoles')
		db_info.get(message.id)

		if db_info is None:
			return

		try:
			role_id = int(db_info[str(message.id)]['used_emojis'][emoji])
		except KeyError:

			return

		role = guild.get_role(role_id)

		await user.remove_roles(role)

	async def parse_payload(self, payload):
		guild = self.bot.get_guild(payload.guild_id)
		channel = guild.get_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)
		user = guild.get_member(payload.user_id)

		emoji = str(payload.emoji)
		return guild, channel, message, user, emoji

	async def fix_message(self, orig_category, guild, message_id):
		my_order = self.updating[guild].get(message_id, 0)
		self.updating[guild][message_id] = my_order + 1
		last = self.updating[guild][message_id]
		await asyncio.sleep(10)
		while self.updating[guild][message_id] != last:
			last = self.updating[guild][message_id]
			await asyncio.sleep(5)
		if my_order + 1 != last:
			return

		category = fix_separator_indexes(dict(orig_category), guild)
		txt, category = make_message(category, guild.roles)

		if category['used_emojis'] != orig_category['used_emojis'] or category['readable_name'] != orig_category['readable_name']:
			channel = guild.get_channel(category['channel_id'])
			message = await channel.fetch_message(message_id)
			await message.edit(content=txt)
			await message.clear_reactions()
			for e in emojis:
				if e in category['used_emojis'].keys():
					await message.add_reaction(e)
				# print(e)

		await db.update_setting(guild.id, 'reactionRoles', {"$set": {str(message.id): category}})


def setup(bot):
	bot.add_cog(ReactionRoles(bot))
