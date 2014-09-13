__author__ = 'ghoti'
from errbot import BotPlugin, botcmd

class PingBot(BotPlugin):
    """Grab the attention of a pingable member in Bootcamp"""
    @botcmd
    def ping(self, mess, args):
        yield "A ping is being requested!"
        #hardcoding the shit out of this for now, plans include pulling ldap info from j4lp.com and roster list
        #from room to avoid clutter and such  gross
        yield "rina_kondur chainsaw_mcginny otsdarva_iv tactically_superior_avacado tujiko_noriko"
        yield "bowervvick_wowbagger impeh_man fenrir_vice vadrin_hegirin alistair_croup"