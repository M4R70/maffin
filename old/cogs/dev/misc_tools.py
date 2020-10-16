# -*- coding: utf-8 -*-

from discord.ext import commands
import discord


class misc_tools(commands.Cog):
    """The description for Misc_Tools goes here."""

    def __init__(self, bot):
        self.bot = bot

    def validate_settings(self, settings, guild):
        return True

    @commands.command()
    async def m(self, ctx, *, name):
        await ctx.send(fake_mention(ctx.guild, name))

    @commands.command()
    async def line(self, ctx):
        print("\n -------------------------------- \n \n")


def fake_mention(guild, name):
    roles = guild.roles
    try:
        r = list(filter(lambda x: x.name == name, roles))
        return f"`<@&{r[0].id}>`"
    except IndexError:
        return "Role not found :x:"

def setup(bot):
    bot.add_cog(misc_tools(bot))
