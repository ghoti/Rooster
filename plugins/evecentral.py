__author__ = 'ghoti'
from errbot import BotPlugin, botcmd
import os
import argparse
import sqlite3
import requests
import xml.etree.ElementTree as ET

EVESTATICDATADUMP = os.getcwd() + '/static.db'

#system = 30000142 jita
#region = 10000002 forge

class EveCentral(BotPlugin):

    @botcmd(split_args_with=' ')
    def price(self, message, args):
        '''usage:!price item [-r region | -s system]'''

        if args == ['']:
            yield "NEED SOMETHING TO PRICE DUMDUM"
            return

        #argparse initializing, this kinda overrides errbots arg handler and makes -h ugly, but.. meh
        parser = argparse.ArgumentParser()
        parser.add_argument('item', type=str, nargs='+')
        where = parser.add_mutually_exclusive_group()
        where.add_argument('-r', metavar='region', type=str, default=None, nargs='+')
        where.add_argument('-s', metavar='system', type=str, default=None, nargs='+')
        pricelookup = parser.parse_args(args=args)

        #first we parse out and grab our item and itemid, or bail completely if that item cant be found
        if not isinstance(pricelookup.item, str):
            #special case for plex since its easily the most common search
            if pricelookup.item[0].lower() == 'plex':
                itemstoprice = self.get_type_id(self, 'license')
            else:
                itemstoprice = self.get_type_id(self, ' '.join(pricelookup.item))
        else:
                itemstoprice = self.get_type_id(self, pricelookup.item)

        if not itemstoprice:
            #i have no idea why err is refusing to return this string, but this ugly hackmakes it work.  wtfbbqlol
            yield "Could not find search item: {0}".format(' '.join(args))
            return

        #if a region is specified, grab the region name and regionid
        if pricelookup.r:
            system = None
            if not isinstance(pricelookup.r, str):
                region = self.get_region(self, ' '.join(pricelookup.r))
            else:
                region = self.get_region(self, pricelookup.r)
        #or system if that is what we want instead
        elif pricelookup.s:
            region = None
            if not isinstance(pricelookup.s, str):
                system = self.get_system(self, ' '.join(pricelookup.s))
            else:
                system = self.get_system(self, pricelookup.s)

        #if no region or system specified, defulat to jita, because.. well duh
        if (pricelookup.r is None and pricelookup.s is None) or (region is None and system is None):
            system = self.get_system(self, 'Jita')
            region = None


        if region:
            yield 'Searching for {} in region {}'.format(pricelookup.item, region[0])
        elif system:
            yield 'Searching for {} in system {}'.format(pricelookup.item, system[0])
        else:
            #more of the same err being picky
            yield "I literally can't even"
            return

        #send all our id's to evecentral and make babbies happen
        prices = {}
        if isinstance(itemstoprice, tuple):
            prices[itemstoprice[0]] = self.evecentralprice(self, itemstoprice, region, system)
            if prices[itemstoprice[0]] is None:
                del prices[itemstoprice[0]]
        else:
            for item in itemstoprice:
                prices[item[0]] = self.evecentralprice(self, item, region, system)
                if prices[item[0]] is None:
                    del prices[item[0]]

        if prices:
            yield
            for name in prices:
                yield "{} : {}".format(name, prices[name])
                #return '\n'+',\n'.join([' : '.join((k, str(prices[k]))) for k in sorted(prices, key=prices. get, reverse=False)])
        else:
            yield "Item not found or no volume in market (NONE FOR SELL)"
            return

    @staticmethod
    def evecentralprice(self, itemid, region, system):
        if region:
            EVE_CENTRAL_QUERY = "http://api.eve-central.com/api/marketstat?typeid={item}&regionlimit={region}"
            pricexml = requests.get(EVE_CENTRAL_QUERY.format(item=itemid[1], region=region[1]))
        elif system:
            EVE_CENTRAL_QUERY = "http://api.eve-central.com/api/marketstat?typeid={item}&usesystem={system}"
            pricexml = requests.get(EVE_CENTRAL_QUERY.format(item=itemid[1], system=system[1]))
        else:
            EVE_CENTRAL_QUERY = "http://api.eve-central.com/api/marketstat?typeid={item}&usesystem={system}"
            pricexml = requests.get(EVE_CENTRAL_QUERY.format(item=itemid[1], system=30000142))
        try:
            root = ET.fromstring(pricexml.text)
            item = root[0][0]
            volume = float(item.find('all').find('volume').text)
            if volume:
                price = {"maxbuy": float(item.find('buy').find('max').text),
                         "minsell": float(item.find('sell').find('min').text)}
                return '{:,} Sell Price | {:,} Buy price'.format(price['minsell'], price['maxbuy'])
            else:
                return
        except:
            return 'ERROR at eve-central! PANIC'

    @staticmethod
    def get_type_id(self, name):
        try:
            conn = sqlite3.connect(EVESTATICDATADUMP)
        except:
            return "Something terrible has happened to my database!"
        try:
            c = conn.cursor()
            c.execute("select typeName, typeID from invTypes where typeName = '{0}' collate nocase;".format(name.strip()))
            result = c.fetchall()
            if len(result) < 1:
                c.execute("select typeName, typeID from invTypes where typeName like '%{0}%' collate nocase;".format(name.strip()))
                results = c.fetchall()
                results = sorted(results, key=lambda x: len(x[0]))
                return results[:5]
            if len(result) == 1:
                return result[0]
            if not result:
                return None
        #wolol panic on all errors
        except:
            return

    @staticmethod
    def get_region(self, place):
        try:
            conn = sqlite3.connect(EVESTATICDATADUMP)
        except:
            return "Something terrible has happened to my database!"
        try:
            c = conn.cursor()
            c.execute("select regionName, regionID from mapRegions where regionName = '{}' collate nocase;".format(place))
            result = c.fetchall()
            if len(result) < 1:
                c.execute("select regionName, regionID from mapRegions where regionName like '%{}%' collate nocase".format(place))
                results = c.fetchall()
                #results = sorted(results, key=lambda x: len(x[0]))
                return results[0]
            if len(result) == 1:
                return result[0]
            if not result:
                return None
        except:
            return None

    @staticmethod
    def get_system(self, place):
        try:
            conn = sqlite3.connect(EVESTATICDATADUMP)
        except:
            return "Something terrible has happened to my database!"
        try:
            c = conn.cursor()
            c.execute("select solarSystemName, solarSystemID from mapSolarSystems where solarSystemName = '{}' collate nocase;".format(place))
            result = c.fetchall()
            if len(result) < 1:
                c.execute("select solarSystemName, solarSystemID from mapSolarSystems where solarSystemName like '%{}%' collate nocase".format(place))
                results = c.fetchall()
                #results = sorted(results, key=lambda x: len(x[0]))
                return results[0]
            if len(result) == 1:
                return result[0]
            if not result:
                return None
        except:
            return None

