from discord.ext import commands
import discord
import utils.db as db
from utils.checks import dev,is_cog_enabled
import asyncio
from collections import defaultdict

emojis = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣',
		  '🔟', '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮',
		  '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸',
		  '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']  # no se ven en pycharm pero hay emojis 1-10 a-z


def make_message(category_data, all_guild_roles):
	msg =''
	if not category_data['first']:
		msg += '\u200b\n'
		print('asd')
	msg +=  category_data['readable_name'] + ':\n'
	used_emojis = {}
	j = 0
	for i in reversed(range(category_data['bottom_separator_index'] + 1, category_data['top_separator_index'])):
		r = all_guild_roles[i]
		emoji = emojis[j]
		j+=1
		msg += ':small_blue_diamond:  ' + emoji + ' ' + fake_mention(r) + '\n'
		used_emojis[emoji] = r.id
	category_data['used_emojis'] = used_emojis
	if category_data['exclusive']:
		msg+= '\n NOTE: *you may only have one of the roles in this category*'



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
		update = {}
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
			if len(to_unset) > 0:
				unset = {x:1 for x in to_unset}
				await db.update_setting(ctx.guild.id, 'reactionRoles', {"$unset": unset})

		first = True
		bot_user = ctx.guild.get_member(self.bot.user.id)
		if bot_user.guild_permissions.mention_everyone and flag != "-f":
			await ctx.send('remove mention everyone permission from bot or use -f flag')
			return
		roles = ctx.guild.roles
		for i in reversed(range(len(roles))):
			r = roles[i]
			if r.name.startswith('<' + groupPrefix):
				category_data = {}
				for j in range(r.position, 0,-1):
					if roles[j].name.startswith('</' + groupPrefix):
						category_data["top_separator_index"] = i
						category_data["bottom_separator_index"] = j
						category_data['exclusive'] = False
						category_data['groupPrefix'] = groupPrefix
						category_data['channel_id'] = ctx.channel.id
						category_data['bottom_separator_id'] = roles[j].id
						category_data['top_separator_id'] = roles[i].id
						readable_name = r.name[len(groupPrefix) + 2:-1]

						if readable_name.endswith('_ex'):
							readable_name = readable_name[:-3]
							category_data['exclusive'] = True

						readable_name = readable_name.strip()
						category_data['readable_name'] = readable_name
						category_data['first'] = first
						first = False
						txt, category_data = make_message(category_data, roles)
						used_emojis = category_data['used_emojis']

						message = await ctx.send(txt)

						for e in emojis:
							if e in used_emojis.keys():
								await message.add_reaction(e)
							else:
								break
						update[str(message.id)] = category_data
						break
		await db.update_setting(ctx.guild.id, 'reactionRoles',
								{"$set": update})
		await ctx.message.delete()


	@dev()
	@commands.command()
	async def rr_update(self,ctx, flag=None):
		"""update existing reaction role messages"""
		bot_user = ctx.guild.get_member(self.bot.user.id)
		if bot_user.guild_permissions.mention_everyone and flag != "-f":
			await ctx.send('remove mention everyone permission from bot or use -f flag')
			return
		guild = ctx.guild
		db_info = await db.get_setting(guild.id, 'reactionRoles')
		del db_info['_id']
		del db_info['field_name']
		for message_id, category in db_info.items():
			await self.fix_message(category, guild, message_id)
		await ctx.message.delete()



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
					r = guild.get_role(role_id)
					await user.remove_roles(r)
		await user.add_roles(role)
		await message.remove_reaction(emoji,user)


	async def parse_payload(self, payload):
		guild = self.bot.get_guild(payload.guild_id)
		channel = guild.get_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)
		user = guild.get_member(payload.user_id)

		emoji = str(payload.emoji)
		return guild, channel, message, user, emoji

	async def fix_message(self, orig_category, guild, message_id):

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

	async def cog_check(self, ctx):
		res = await is_cog_enabled(ctx)
		return res

def setup(bot):
	bot.add_cog(ReactionRoles(bot))
