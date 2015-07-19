# -*- coding: utf-8 -*-

from __future__ import with_statement

import pycurl
import re

from base64 import b64encode

from module.network.RequestFactory import getRequest as get_request
from module.plugins.internal.Hook import Hook, threaded


class ImageTyperzException(Exception):

    def __init__(self, err):
        self.err = err


    def get_code(self):
        return self.err


    def __str__(self):
        return "<ImageTyperzException %s>" % self.err


    def __repr__(self):
        return "<ImageTyperzException %s>" % self.err


class ImageTyperz(Hook):
    __name__    = "ImageTyperz"
    __type__    = "hook"
    __version__ = "0.08"

    __config__ = [("username"    , "str"     , "Username"                        , ""  ),
                  ("password"    , "password", "Password"                        , ""  ),
                  ("check_client", "bool"    , "Don't use if client is connected", True)]

    __description__ = """Send captchas to ImageTyperz.com"""
    __license__     = "GPLv3"
    __authors__     = [("RaNaN"   , "RaNaN@pyload.org"   ),
                       ("zoidberg", "zoidberg@mujmail.cz")]


    SUBMIT_URL = "http://captchatypers.com/Forms/UploadFileAndGetTextNEW.ashx"
    RESPOND_URL = "http://captchatypers.com/Forms/SetBadImage.ashx"
    GETCREDITS_URL = "http://captchatypers.com/Forms/RequestBalance.ashx"


    def get_credits(self):
        res = self.load(self.GETCREDITS_URL,
                     post={'action': "REQUESTBALANCE",
                           'username': self.get_config('username'),
                           'password': self.get_config('password')})

        if res.startswith('ERROR'):
            raise ImageTyperzException(res)

        try:
            balance = float(res)
        except Exception:
            raise ImageTyperzException("Invalid response")

        self.log_info(_("Account balance: $%s left") % res)
        return balance


    def submit(self, captcha, captchaType="file", match=None):
        req = get_request()
        #: Raise timeout threshold
        req.c.setopt(pycurl.LOW_SPEED_TIME, 80)

        try:
            #@NOTE: Workaround multipart-post bug in HTTPRequest.py
            if re.match("^\w*$", self.get_config('password')):
                multipart = True
                data = (pycurl.FORM_FILE, captcha)
            else:
                multipart = False
                with open(captcha, 'rb') as f:
                    data = f.read()
                data = b64encode(data)

            res = self.load(self.SUBMIT_URL,
                            post={'action': "UPLOADCAPTCHA",
                                  'username': self.get_config('username'),
                                  'password': self.get_config('password'), 'file': data},
                            multipart=multipart,
                            req=req)
        finally:
            req.close()

        if res.startswith("ERROR"):
            raise ImageTyperzException(res)
        else:
            data = res.split('|')
            if len(data) == 2:
                ticket, result = data
            else:
                raise ImageTyperzException("Unknown response: %s" % res)

        return ticket, result


    def captcha_task(self, task):
        if "service" in task.data:
            return False

        if not task.isTextual():
            return False

        if not self.get_config('username') or not self.get_config('password'):
            return False

        if self.core.isClientConnected() and self.get_config('check_client'):
            return False

        if self.get_credits() > 0:
            task.handler.append(self)
            task.data['service'] = self.__name__
            task.setWaiting(100)
            self._process_captcha(task)

        else:
            self.log_info(_("Your %s account has not enough credits") % self.__name__)


    def captcha_invalid(self, task):
        if task.data['service'] == self.__name__ and "ticket" in task.data:
            res = self.load(self.RESPOND_URL,
                         post={'action': "SETBADIMAGE",
                               'username': self.get_config('username'),
                               'password': self.get_config('password'),
                               'imageid': task.data['ticket']})

            if res == "SUCCESS":
                self.log_info(_("Bad captcha solution received, requested refund"))
            else:
                self.log_error(_("Bad captcha solution received, refund request failed"), res)


    @threaded
    def _process_captcha(self, task):
        c = task.captchaFile
        try:
            ticket, result = self.submit(c)
        except ImageTyperzException, e:
            task.error = e.getCode()
            return

        task.data['ticket'] = ticket
        task.setResult(result)
