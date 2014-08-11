__author__ = 'ghoti'
from errbot import BotPlugin, botcmd

class Smiles(BotPlugin):
    """Plugin to link the emoticon page on j4lp.com"""
    @botcmd
    def smiles(self, mess, args):
        yield "I hear you need some smiles in your life:"
        yield "http://j4lp.com/smillies/"