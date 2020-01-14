from discord.ext import commands
from discord import client
import discord
import asyncio
import timeago
import datetime
import sys
import traceback

class errorHandling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def validate_settings(self, settings, guild):
        return True

    async def report(self, cog, message):
        print(f"errorHandling: {cog}: " + message)

    async def dev_report(self, cog, message):
        print(f"dev: {cog}: " + message)

    async def try_to_send(channel, cog, text=None, embed=None, file=None):
        await channel.send(content=message, embed=embed)


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception

        https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
        """


        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):

            return

        ignored = (commands.CommandNotFound, commands.UserInputError)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        # if isinstance(error, ignored):
        #     print('2')
        #     return

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CheckFailure):
            return

        # All other Errors not returned come here... And we can just print the default TraceBack.
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)





def setup(bot):
    bot.add_cog(errorHandling(bot))
