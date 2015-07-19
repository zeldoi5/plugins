# -*- coding: utf-8 -*-

import re
import time

from module.plugins.internal.Account import Account


class MegaRapidCz(Account):
    __name__    = "MegaRapidCz"
    __type__    = "account"
    __version__ = "0.37"

    __description__ = """MegaRapid.cz account plugin"""
    __license__     = "GPLv3"
    __authors__     = [("MikyWoW", "mikywow@seznam.cz"),
                       ("zoidberg", "zoidberg@mujmail.cz")]


    login_timeout = 60

    LIMITDL_PATTERN = ur'<td>Max. počet paralelních stahování: </td><td>(\d+)'
    VALID_UNTIL_PATTERN = ur'<td>Paušální stahování aktivní. Vyprší </td><td><strong>(.*?)</strong>'
    TRAFFIC_LEFT_PATTERN = r'<tr><td>Kredit</td><td>(.*?) GiB'


    def load_account_info(self, user, req):
        htmll = self.load("http://megarapid.cz/mujucet/")

        m = re.search(self.LIMITDL_PATTERN, htmll)
        if m:
            data = self.get_account_data(user)
            data['options']['limitDL'] = [int(m.group(1))]

        m = re.search(self.VALID_UNTIL_PATTERN, htmll)
        if m:
            validuntil = time.mktime(time.strptime(m.group(1), "%d.%m.%Y - %H:%M"))
            return {'premium': True, 'trafficleft': -1, 'validuntil': validuntil}

        m = re.search(self.TRAFFIC_LEFT_PATTERN, htmll)
        if m:
            trafficleft = float(m.group(1)) * (1 << 20)
            return {'premium': True, 'trafficleft': trafficleft, 'validuntil': -1}

        return {'premium': False, 'trafficleft': None, 'validuntil': None}


    def login(self, user, data, req):
        html = self.load("http://megarapid.cz/prihlaseni/")

        if "Heslo:" in html:
            start = html.index('id="inp_hash" name="hash" value="')
            html = html[start + 33:]
            hashes = html[0:32]
            html = self.load("https://megarapid.cz/prihlaseni/",
                             post={'hash'    : hashes,
                                   'login'   : user,
                                   'pass1'   : data['password'],
                                   'remember': 1,
                                   'sbmt'    : u"Přihlásit"})
