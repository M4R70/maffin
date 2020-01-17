# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import utils.db
import datetime


class moderation(commands.Cog):
    """The description for Moderation goes here."""

    def __init__(self, bot):
        self.bot = bot

    def validate_settings(self, settings, guild):
        try:
            if settings["enabled"]:
                return True

        except KeyError as e:
            return f"logs: Missing field: enabled"

        return True

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.voice.mute:
            await  utils.db.updateOne('anti_mute_avoid', {'guild_id': member.guild.id, 'user_id': member.id},
                                      {'$set': {'date': datetime.datetime.now()}})

    @commands.Cog.listener()
    async def on_member_join(self, member):
        db_info = await utils.db.findOne('anti_mute_avoid', {'guild_id': member.guild.id, 'user_id': member.id})

        if db_info is not None:
            await utils.db.updateOne('to_mute_unmute', {'guild_id': member.guild.id, 'user_id': member.id},
                                     {'$set': {'action': 'mute'}})
            wait
            await utils.db.deleteOne('anti_mute_avoid', {'guild_id': member.guild.id, 'user_id': member.id})
            # await member.edit(mute=True,reason='Anti mute avoid')

    # @commands.has_permissions(mute_members=True)
    @commands.command()
    async def mute(self, ctx, member: discord.Member):
        vc = ctx.guild.voice_channels[0]
        if not vc.permissions_for(ctx.author).mute_members:
            return
        try:
            await member.edit(mute=True)
            await ctx.send(f"{member} was muted :thumbsup:")
        except:
            await utils.db.updateOne('to_mute_unmute', {'guild_id': member.guild.id, 'user_id': member.id},
                                     {'$set': {'action': 'mute'}})
            await ctx.send(f'{member} will be muted :thumbsup:')

    # @commands.has_permissions(mute_members=True)
    @commands.command()
    async def unmute(self, ctx, member: discord.Member):
        vc = ctx.guild.voice_channels[0]
        if not vc.permissions_for(ctx.author).mute_members:
            return
        try:
            await member.edit(mute=False)
            await  ctx.send(f"{member} was unmuted :thumbsup:")
        except:
            await utils.db.updateOne('to_mute_unmute', {'guild_id': member.guild.id, 'user_id': member.id},
                                     {'$set': {'action': 'unmute'}})

            await ctx.send(f"{member} will be unmuted :thumbsup:")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel:
            if before.channel is None or before.afk and after.channel is not None:
                db_info = await utils.db.findOne('to_mute_unmute', {'guild_id': member.guild.id, 'user_id': member.id})
                if db_info is not None:
                    if db_info['action'] == 'mute':
                        await member.edit(mute=True)
                    elif db_info['action'] == 'unmute':
                        await member.edit(mute=False)
                    else:
                        print('weird error on moderation, voice_state_update')

                await utils.db.deleteOne('to_mute_unmute',{'guild_id': member.guild.id, 'user_id': member.id})

def setup(bot):
    bot.add_cog(moderation(bot))
