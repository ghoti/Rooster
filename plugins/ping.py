from os.path import isfile
from errbot import BotPlugin, botcmd


class Ping(BotPlugin):
    """A Ping Group function for Err"""
    min_err_version = '1.6.0'  # Optional, but recommended

    ping_groups_file = 'pings.txt'

    def __init__(self):
        super().__init__()
        try:
            self.user_groups = self.init_groups()
        except FileNotFoundError:
            self.user_groups = self.init_groups()

    @botcmd(split_args_with=None)
    def ping(self, mess, args):
        """Ping a specified group"""

        if not args:
            return "No Group to Ping, valid groups are {}".format(", ".join(self.user_groups))

        qry = args.lowercase

        if qry in self.user_groups:
            return " ".join(self.user_groups[args])
        else:
            return "No such group, valid groups are: %s" % (", ".join(self.user_groups))

    @botcmd(split_args_with=None)
    def ping_groups(self, mess, args):
        """Show the groups that can be pinged"""

        return ", ".join(self.user_groups)

    def init_groups(self):
        """
        Reads groups from file, format for the file is:
         - one group per line,
         - Name is separated from content with a fat, right-facing arrow (=>)
         - lines separated with \n.

         Will (re)make the file with default groups if the file is missing, then call itself again.

        Since: 2015-08-07
        :return: dictionary containing the groups in self.ping_groups_file
        """
        if isfile(self.ping_groups_file):
            with open(self.ping_groups_file) as f:
                raw_groups = [lines for lines in f]

            group_dict = {}
            for group in raw_groups:
                for key, value in group.split(" => "):
                    group_dict[key] = value

            return group_dict
        else:
            s = ("hr => shadowozera1, chainsaw_mcginny, wocks_zhar\n"
                 "fweight => umnumun, umnumun_work, Inspector Gair\n"
                 "leadership => rina_kondur, chainsaw_mcginny, alistair_croup, ipoopedbad_ernaga\n"
                 "admin => vadrin_hegirin, chainsaw_mcginny\n"
                 "gas => :jihad:\n"
                 "chinslaw => :godwinning:\n")

            with open(self.ping_groups_file, 'x') as f:
                f.write(s)

            raise FileNotFoundError

    @botcmd(split_args_with=None)
    def ping_write(self, mess, args):
        """
        Writes the contents of self.ping_groups to self.ping_group_file, serializing any changes made to it.
        """
        with open(self.ping_groups_file, 'w') as f:
            for key, value in self.ping_groups:
                f.write(key + " => " + value + "\n")

    # Leave this in I guess? I don't really know if it's used still.
    def __getitem__(self, key):
        try:
            return super(Ping, self).__getitem__(key)
        except KeyError:
            return None
