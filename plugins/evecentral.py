__author__ = 'ghoti'
from errbot import BotPlugin, botcmd

import os
import requests
import sqlite3
import xml.etree.ElementTree as ET


EVESTATICDATADUMP = os.getcwd() + '\static.db'

#currently defaults to jita, but someday might include a search feature for other regions
#EVECENTRAL = "http://api.eve-central.com/api/marketstat?typeid={0}&minQ=1&&regionlimit=10000002"
EVE_CENTRAL_QUERY="http://api.eve-central.com/api/marketstat?typeid={item}&regionlimit={region}"
JITA_REGION_ID='10000002'


class EveCentral(BotPlugin):
    """EVECentral Plugin for all your market data"""
    @botcmd(split_args_with=' ')
    def price(self, message, args):
        """!price <search item> returns the regional market buy and sell prices for up to 5 search results, or 1 if
        direct match is found"""
        if not args[0]:
            return 'Do you want me to guess what to price?'
        #add a special case for plex, since searching for plex results in complexes and other odd items
        if args[0].lower() == 'plex':
            itemstoprice = self.get_type_id(self, '30 Day')
        else:
            itemstoprice = self.get_type_id(self, ' '.join(args))
        if not itemstoprice:
            return "Could not find search item: {0}".format(' '.join(args))
        prices = dict()
        for item in itemstoprice:
            #we call the same api twice which is probably bad, should look into this someday
            if self.volumecheck(self, item[1]):
                prices[item[0]] = self.evecentralprice(self, item[1])
        #return prices
        if not prices:
            return 'No items with search term {0} found with any volume'.format(args)
        return '\n'+',\n'.join([' : '.join((k, str(prices[k]))) for k in sorted(prices, key=prices. get, reverse=False)])

    @staticmethod
    def get_type_id(self, name):
        if os.path.isfile(os.path.expanduser(EVESTATICDATADUMP)):
            conn = sqlite3.connect(EVESTATICDATADUMP)
        else:
            return "Something terrible has happened to my database!"
        try:
            c = conn.cursor()
            c.execute("select typeName, typeID from invTypes where typeName = '{0}' collate nocase;".format(name.strip()))
            result = c.fetchall()
            if len(result) < 1:
                c.execute("select typeName, typeID from invTypes where typeName like '%{0}%' collate nocase;".format(name.strip()))
                results = c.fetchall()
                results = sorted(results, key=lambda x:len(x[0]))
                return results[:5]
            if len(result) == 1:
                return result
            if not result:
                return None
        #wolol panic on all errors
        except:
            return None

    @staticmethod
    def evecentralprice(self, itemid):
        try:
            pricexml = requests.get(EVE_CENTRAL_QUERY.format(item=itemid, region=JITA_REGION_ID))
            root = ET.fromstring(pricexml.text)
            item = root[0][0]
            price = {"maxbuy": float(item.find('buy').find('max').text),
                     "minsell": float(item.find('sell').find('min').text), }
            return 'Sell Price: {:,} Isk - Buy Price {:,} Isk'.format(price['minsell'], price['maxbuy'])
        except:
            return 'Error Fetching Price!'

    @staticmethod
    def volumecheck(self, itemid):
        try:
            pricexml = requests.get(EVE_CENTRAL_QUERY.format(item=itemid, region=JITA_REGION_ID))
            root = ET.fromstring(pricexml.text)
            item = root[0][0]
            volume = float(item.find('all').find('volume').text)
            return volume
        #notice a pattern in my style?
        except:
            return None