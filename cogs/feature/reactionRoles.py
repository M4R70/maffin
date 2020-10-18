from discord.ext import commands
import discord
import utils.db as db
from utils.checks import dev

emojis = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣',
		  '🔟', '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮',
		  '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸',
		  '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']  # no se ven en pycharm pero hay emojis 1-10 a-z


def make_message(category_data, roles):
	msg = '\u200b\n' + category_data['readable_name'] + ':\n'
	used_emojis = {}
	for i in range(category_data['bottom_separator_index'] + 1, category_data['top_separator_index']):
		r = roles[i]
		emoji = emojis[i - category_data['bottom_separator_index'] - 1]
		msg += ':small_blue_diamond:  ' + emoji + ' ' + fake_mention(r) + '\n'
		used_emojis[emoji] = r.id
	category_data['used_emojis'] = used_emojis

	return msg, category_data


def fake_mention(role):
	return f"<@&{role.id}>"


class ReactionRoles(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.default_emojis = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣',
							   # no se ven en pycharm pero hay emojis 1-10 a-z
							   '🔟', '🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮',
							   '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸',
							   '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']

	@dev()
	@commands.command()
	async def post_rr_group(self, ctx, groupPrefix: str, flag=None):
		"""Post a group of reaction role categories"""

		db_info = await db.get_setting(ctx.guild.id, 'reactionRoles')
		ids = list(db_info.keys())
		to_unset = []
		for msg_id in ids:
			channel = ctx.guild.get_channel(db_info.get('channel_id'))
			if channel is None:
				to_unset.append(msg_id)
			else:
				msg = await channel.fetch_message(msg_id)
				if msg is None:
					to_unset.append(msg_id)

			for x in to_unset:
				if x not in ["_id",'field_name']:
					await db.update_setting(ctx.guild.id, 'reactionRoles', {"$unset": {x:True}})

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

						await db.update_setting(ctx.guild.id, 'reactionRoles',
												{"$set": {str(message.id): category_data}})
						break

	@commands.Cog.listener()
	async def on_raw_reaction_add(self, payload):
		guild, channel, message, user, emoji = await self.parse_payload(payload)

		db_info = await db.get_setting(guild.id, 'reactionRoles')
		db_info.get(message.id)

		if db_info is None:
			return
		try:
			role_id = int(db_info[str(message.id)]['used_emojis'][emoji])
		except KeyError:
			return
		role = guild.get_role(role_id)
		await user.add_roles(role)

	async def parse_payload(self, payload):
		guild = self.bot.get_guild(payload.guild_id)
		channel = guild.get_channel(payload.channel_id)
		message = await channel.fetch_message(payload.message_id)
		user = guild.get_member(payload.user_id)

		emoji = str(payload.emoji)
		return guild, channel, message, user, emoji


def setup(bot):
	bot.add_cog(ReactionRoles(bot))
