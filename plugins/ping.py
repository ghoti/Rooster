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

    def __del__(self):
        self.ping_write()

    # Bot Commands
    # =========================================================================

    @botcmd(split_args_with=None)
    def ping(self, mess, args):
        """Ping a specified group"""

        if not args:
            return "No Group to Ping, valid groups are {}" \
                .format(", ".join(self.user_groups))

        qry = args.lowercase

        if qry in self.user_groups:
            return " ".join(self.user_groups[qry])
        else:
            return "No such group, valid groups are: {}" \
                   .format(", ".join(self.user_groups))

    @botcmd(split_args_with=None)
    def ping_groups(self, mess, args):
        """Show the groups that can be pinged"""

        return ", ".join(self.user_groups)

    @botcmd(split_args_with=None)
    def ping_set(self, mess, args):
        if not args:
            return "Can't set nothing to nothing. Fix it, dumdum."

        qry = args.split(" => ")

        if not qry[1]:
            return "Use correct formatting. Format is: " \
                   "!ping_set group => list of people"

        self.ping_groups[qry[0]] = qry[1]
        return "Setting {} to {}...".format(qry[0], qry[1])

    @botcmd(split_args_with=None)
    def ping_write(self, mess, args):
        """
        Writes the contents of self.ping_groups to self.ping_group_file,
        serializing any changes made to it.

        Since: 2015-08-07
        """
        with open(self.ping_groups_file, 'w') as f:
            for key, value in self.ping_groups:
                f.write(key + " => " + value + "\n")

    @botcmd(split_args_with=None)
    def poop(self, mess, args):
        return "You and poop are friends."

    # Internal auxiliary methods.
    # =========================================================================

    def init_groups(self):
        """
        Reads groups from file, format for the file is:
         - one group per line,
         - Name is separated from content with a fat, right-facing arrow (=>)
         - lines separated with \n.

         Will (re)make the file with default groups if the file is missing,
         but raise a FileNotFoundException, so it can be caught and the method
         called again.

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
                 "leadership => rina_kondur, chainsaw_mcginny, alistair_croup, "
                 "ipoopedbad_ernaga\n"
                 "admin => vadrin_hegirin, chainsaw_mcginny\n"
                 "gas => :jihad:\n"
                 "chinslaw => :godwinning:\n")

            with open(self.ping_groups_file, 'x') as f:
                f.write(s)

            raise FileNotFoundError

    # Leave this in I guess? I don't really know if it's used still.
    def __getitem__(self, key):
        try:
            return super(Ping, self).__getitem__(key)
        except KeyError:
            return None
