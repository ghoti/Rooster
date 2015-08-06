from errbot import BotPlugin, botcmd

class Ping(BotPlugin):

    """A Ping Group function for Err"""
    min_err_version = '1.6.0'  # Optional, but recommended

    # replacement system for the shelf bullshit
    HR = ('nivlac_hita', 'shadowozera1', 'chainsaw_mcginny')
    Leadership = ('rina_kondur', 'chainsaw_mcginny', 'alistair_croup', 'ipoopedbad_ernaga')
    admin = ('vadrin_hegirin', 'chainsaw_mcginny')
    user_groups = {'HR': HR, 'Leadership': Leadership, 'admin': admin}
        
    @botcmd(split_args_with=None)
    def ping(self, mess, args):
        """Ping a specified group"""

        if not args:
            return "No Group to Ping, valid groups are {}".format(", ".join(self.user_groups))
        
        if args in self.user_groups:
            return ", ".join(self.user_groups[args])
        else:
            return "No such group, valid groups are: %s" % (", ".join(self.user_groups))
            
    @botcmd(split_args_with=None)
    def ping_groups(self, mess, args):
        """Show the groups that can be pinged"""
        
        return ", ".join(self.user_groups)

    # Leave this in I guess? I don't really know if it's used still.
    def __getitem__(self, key):
        try:
            return super(Ping, self).__getitem__(key)
        except KeyError:
            return None