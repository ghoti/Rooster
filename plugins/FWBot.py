__author__ = 'ghoti'
from errbot import BotPlugin, botcmd
import arrow
import evelink.map
import os
import sqlite3

EVESTATICDATADUMP = os.getcwd() + '/static.db'


class FWBot(BotPlugin):
    """Faction war bot for all your Faction Warfare needs"""

    @botcmd(split_args_with=' ')
    def fw(self, mess, args):
        """!fw <system> will return the current fw status of a system including contention rates"""
        if not args[0]:
            return "Should I guess the system for you...?"
        api = evelink.map.Map()
        flist = api.faction_warfare_systems()
        if os.path.isfile(os.path.expanduser(EVESTATICDATADUMP)):
            conn = sqlite3.connect(EVESTATICDATADUMP)
        else:
            conn = None
            return "Error in db?!"
        try:
            c = conn.cursor()
            #just in case there is an exact match to our input instead of trying to search through, i dunno
            try:
                c.execute("select itemID from mapDenormalize where itemName = '{0}' collate nocase".format(args[0]))
                systemid = c.fetchone()[0]
            except:
                c.execute("select itemID from mapDenormalize where itemName like '%{0}%' collate nocase".format(
                    args[0]))
                systemid = c.fetchone()[0]

            name = flist.result[systemid]['name']
            tstamp = arrow.get(flist.expires).humanize()
            owner = flist.result[systemid]['owner']['name']
            occupier = flist.result[systemid]['occupier']['name']
            #API reports None as occupier is the owner actually owns the system.
            if occupier is None:
                occupier = owner

            if flist.result[systemid]['contested']:
                vp = flist.result[systemid]['vp']
                needed = flist.result[systemid]['vpneeded']
                pcent = "{0:.1f}%".format(float(vp/needed*100))

                return "{}: Currently occupied by the {} is {} contested! (new data {})".format(
                    name, occupier, pcent, tstamp)
            else:
                return "{}: Currently occupied by the {} is stable! (new data {})".format(name, occupier, tstamp)
        #any error just tell the user they are dum
        except Exception:
            return "System {} not found or not in FW".format(args[0])