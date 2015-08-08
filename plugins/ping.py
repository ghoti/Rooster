from os.path import isfile
from errbot import BotPlugin, botcmd
import json


class Ping(BotPlugin):
    """A Ping Group function for Err"""
    min_err_version = '1.6.0'  # Optional, but recommended

    ping_groups_file = 'pings.json'

    def __init__(self):
        super().__init__()
        self.ping_groups = self.init_groups()

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

        qry = str(args)
        sep = ' => '

        if sep in qry:
            raw_group = qry[:qry.find(sep)]
            raw_content = qry[qry.find(sep) + len(sep):]

            self.ping_groups[raw_group] = raw_content
            return "Setting {} to {}...".format(raw_group, raw_content)

        else:
            return "Correct format is: group{}content".format(sep)

    @botcmd(split_args_with=None)
    def ping_write(self, mess, args):
        """
        Writes the contents of self.ping_groups to self.ping_group_file,
        serializing any changes made to it.

        Since: 2015-08-07
        """
        with open(self.ping_groups_file, 'w') as f:
            json.dump(self.ping_groups, f, indent=4)

    @botcmd(split_args_with=None)
    def poop(self, mess, args):
        return "You and poop are friends."

    # Internal auxiliary methods.
    # =========================================================================

    def init_groups(self):
        """
        Reads groups from file, format for the file is json.

        Will (re)make the file with default groups if the file is missing,
        and return the dict.

        Since: 2015-08-08
        :return: dictionary containing the groups in self.ping_groups_file
        """
        if isfile(self.ping_groups_file):
            with open(self.ping_groups_file) as f:
                group_dict = json.load(f)

            return group_dict

        else:
            group_dict = {"hr": "shadowozera1, chainsaw_mcginny, wocks_zhar",
                          "fweight": "umnumun, umnumun_work, Inspector Gair",
                          "leadership": "rina_kondur, chainsaw_mcginny,"
                                        " alistair_croup, ipoopedbad_ernaga",
                          "admin": "vadrin_hegirin, chainsaw_mcginny",
                          "gas": ":jihad:",
                          "chinslaw": ":godwinning:"}

            self.ping_write()
            return group_dict

    # Leave this in I guess? I don't really know if it's used still.
    def __getitem__(self, key):
        try:
            return super(Ping, self).__getitem__(key)
        except KeyError:
            return None
