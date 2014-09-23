#__author__ = 'ghoti'
from errbot import BotPlugin

import csv
import humanize
import logging
import re
import requests

kill_pattern = r"https?:\/\/(?:www.)?zkillboard.com\/kill\/([0-9]+)\/*"
kill_pattern = re.compile(kill_pattern)
ZKILL = 'https://zkillboard.com/api/kills/killID/{}/'

import csv
invtypes = {}
with open('invTypes.csv') as f:
    invreader = csv.reader(f, delimiter=',', quotechar='"')
    for i in invreader:
        invtypes[i[0]] = i[1]

class ZkillWatch(BotPlugin):
    def activate(self):
        super(ZkillWatch, self).activate()
        if not "kills" in self:
            self["kills"] = {}
        logging.debug('bot is alive and shelf is active')

    @staticmethod
    def ship_name(itemId):
        #if itemId in shipTypes:
        #    return shipTypes[itemId]
        #logging.debug('ship {} not found in my list please add'.format(itemId))
        #return "???"
        try:
            ship = invtypes[itemId]
        except KeyError:
            #this should never happen?
            ship = '???'
        return ship

    def zkill(self, killid, mess):
        kill = requests.get(ZKILL.format(killid)).json()
        ship = self.ship_name(kill[0]['victim']['shipTypeID'])
        victim = kill[0]['victim']['characterName']
        victimalliance = kill[0]['victim']['allianceName']
        attackers = 0
        for attacker in kill[0]['attackers']:
            attackers += 1
            if int(attacker['finalBlow']):
                killer = attacker['characterName']
                killeralliance = attacker['allianceName']
        #sometimes zkill doesnt give us a value, odd
        try:
            strValue = kill[0]["zkb"]["totalValue"]
            value = round(float(strValue))
            value = humanize.intword(value)
        except KeyError:
            value = '???'
        self.send(mess.getFrom(), "Victim: {}({})".format(victim, victimalliance), message_type=mess.getType())
        self.send(mess.getFrom(), "Killing Blow: {}({}) ({} other pilot(s) involved)".format(
            killer, killeralliance, attackers-1), message_type=mess.getType())
        self.send(mess.getFrom(), "Ship: {} ({})".format(ship, value), message_type=mess.getType())

    def callback_message(self, conn, mess):
        #WHY THE FUCK DO I HAVE TO CAST THAT AS A STRING
        killmail_id = set(killmail_id for killmail_id in re.findall(kill_pattern, str(mess)))
        for kill in killmail_id:
            logging.debug('Caught a zkill link, doing magic')
            if kill in self["kills"].keys():
                self.send(mess.getFrom(), "REPOST ALERT - SOMEONE ALREADY POSTED THIS KILL SCRUB", message_type=mess.getType())
            else:
                seenkills = self["kills"]
                seenkills[kill] = kill
                self['kills'] = seenkills
            self.zkill(kill, mess)
