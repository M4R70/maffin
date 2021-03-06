# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import utils.db


class prefix(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.default_prefix = '!'
    
    def validate_settings(self, settings, guild):
        return True


    @commands.has_permissions(administrator=True)
    @commands.command()
    async def set_prefix(self, ctx, prefix: str):
        await utils.db.updateOne('prefixes', {'guild_id': ctx.guild.id}, {'$set': {'prefix': prefix}})
        await ctx.send('Prefix changed :thumbsup:')

    @commands.command()
    async def get_prefix(self, ctx):
        message = ctx.message
        db_info = await utils.db.findOne('prefixes', {'guild_id': message.guild.id})
        res = ''
        if db_info is None:
           res = self.default_prefix
        else:
            res = db_info['prefix']

        await ctx.send("This guild's pefix is " + res)

def setup(bot):
    bot.add_cog(prefix(bot))
