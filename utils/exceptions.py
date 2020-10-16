import logging
import traceback
import discord


async def report_meta(e, ctx=None,error_msg=None):
	traceback_print = """**Traceback:**\n```{0}```\n""".format(
		'\n-------\n'.join(traceback.format_exception(None, e, e.__traceback__)))

	if error_msg is not None:
		logging.info(error_msg + '\n\n' + traceback_print)
	if ctx is not None:
		await ctx.send(traceback_print)
