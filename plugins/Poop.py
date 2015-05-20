__author__ = 'ghoti'
from errbot import botcmd, BotPlugin

class tinker(BotPlugin):
    @botcmd
    def poop(self, mess, args):
        print(mess.frm.node + " and ipoopedbad_ernaga are friends.")