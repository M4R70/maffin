from discord.ext import commands
import discord

def dev():
    def predicate(ctx):
        return ctx.message.author.id == 219632772514316289
    return commands.check(predicate)
