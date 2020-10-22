import discord
from discord.ext import commands


async def convert_member(ctx, thing):
	try:
		member = await commands.MemberConverter().convert(ctx, thing)
	except discord.ext.commands.errors.MemberNotFound:
		member = None
	return member


def convert_int(thing, max=None, min=None):
	try:
		n = int(thing)
		if max is not None:
			if n > max:
				return None
		if min is not None:
			if n < min:
				return None
		return n
	except (ValueError,OverflowError):
		return None
