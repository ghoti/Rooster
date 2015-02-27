__author__ = 'ghoti'
from errbot import botcmd, BotPlugin
import evelink.eve
import arrow
import requests

class EveWho(BotPlugin):
    @staticmethod
    def getid(name):
        api = evelink.eve.EVE()
        try:
            person = api.character_id_from_name(name=name)
            return person.result
        except:
            return None

    @staticmethod
    def getkbstats(id):
        try:
            r = requests.get('https://zkillboard.com/api/stats/characterID/{}/'.format(id), timeout=10)
        except TimeoutError:
            return '[N/A, N/A]'
        
        try:
            data = r.json()
        except ValueError: #if character has no killboard things get real real weird
            return '[0, 0]'
        
        if not data:
            return '[0, 0]'

        kills = data["totals"]["countDestroyed"]
        lost = data["totals"]["countLost"]
        return '[{}, {}]'.format(str(kills), str(lost))

    @staticmethod
    def getcharsheet(id):
        api = evelink.eve.EVE()
        person = api.character_info_from_id(id)
        name = person.result['name']
        corp = person.result['corp']['name']
        corpsince = arrow.get(person.result['corp']['timestamp']).humanize()
        alliance = person.result['alliance']['name']
        secstatus = person.result['sec_status']
        secstatus = '%.2f' % secstatus
        secstatus = float(secstatus)
        age = arrow.get(person.result['history'][-1]['start_ts']).humanize()
        return name, corp, corpsince, alliance, secstatus, age

    @staticmethod
    def gethistory(id):
        api = evelink.eve.EVE()
        person = api.character_info_from_id(id)
        corphistory = []
        for corp in person.result['history']:
            corphistory.append('{} - {}'.format(corp['corp_name'], arrow.get(corp['start_ts']).humanize()))
            if len(corphistory) > 4:
                return corphistory
        return corphistory

    @botcmd(split_args_with=' ')
    def who(self, mess, args):
        '''
        Search for player details
        '''
        if not args[0]:
            return 'Should I take a guess at who you are looking for?'
        id = self.getid(' '.join(args))
        if id:
            kbstats = self.getkbstats(id)
            name, corp, corpsince, alliance, secstatus, age = self.getcharsheet(id)
            return '{} {}{} Born {} - {}[{}] - {}'.format(name, secstatus, kbstats, age, corp, corpsince, alliance)
        else:
            return '{} not found. Try again?'.format(' '.join(args))

    @botcmd(split_args_with=' ')
    def who_history(self, mess, args):
        '''
        Show the last 5 corps for a player
        '''
        if not args[0]:  #i cant figure out why err sometimes ignores this.  rather, most of the time.
            yield 'Should I take a guess who you are looking for?'
            return
        id = self.getid(' '.join(args))
        if id:
            corphistory = self.gethistory(id)
            for corp in corphistory:
                yield corp
        else:
            yield '{} was not found.  Try again? (Remember, case sensitive!'.format(' '.join(args))
            return