__author__ = 'ghoti'
from errbot import BotPlugin, botcmd

from trolly.client import Client
from trolly.organisation import Organisation
from trolly.board import Board
from trolly.list import List
from trolly.card import Card
from trolly.checklist import Checklist
from trolly.member import Member
from trolly import ResourceUnavailable

import configparser

class Trello(BotPlugin):
    """Plugin to link the emoticon page on j4lp.com"""
    @botcmd(split_args_with=' ')
    def trello(self, message, args):
        """Usage: !trello <list>
        Returns cards in list from IT board"""

        if not args[0]:
            yield "Required argument list not given"

        config = configparser.ConfigParser()
        config.read_file(open('config/trello.cfg'))
        api_key = config.get('api', 'key')
        user_auth_token = config.get('api', 'auth_token')

        board_id = config.get('board', 'board_id')

        client = Client(api_key, user_auth_token)
        board = Board(client, board_id)

        items = []
        for i in board.get_lists():
            li = i.get_list_information()
            if li['name'] == args[0]:
                for j in i.get_cards():
                    items.append(j.get_card_information()['labels'][0]['name'] + ': ' + j.get_card_information()['name'])

        if  items:
            yield "The following tasks are open in '{}':".format(args[0])
            for i in items:
                yield i
        else:
            yield "No active cards or List {} not found".format(args[0])
