import requests
from lxml import etree
from bs4 import BeautifulSoup
import time
import win32com.client
import socks  #set proxy
import socket #set proxy
import re
import getpass

g_ciId = ''
g_ciWebPage = ''
MAX_LOOP_CI = 30
g_returnResponseText = ''
g_break = False
g_passReason = ''

class Login(object):
    def __init__(self):
        self.headers = {
            'Referer': g_ciWebPage,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'Host': '10.159.215.231:8080'
        }
        self.login_url = 'http://10.159.215.231:8080/login'
        self.post_url = 'http://10.159.215.231:8080/do-login'
        self.logined_url = g_ciWebPage
        self.session = requests.Session()

    def login(self, username, password):
        post_data = {
            'referer': g_ciWebPage,
            'id': username,
            'password': password
        }
        self.logined_url = g_ciWebPage
        self.headers = {
            'Referer': g_ciWebPage,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'Host': '10.159.215.231:8080'
        }

        global g_returnResponseText
        statusCode = 0

        try:
            print('Login: Begin to post web')
            response = self.session.post(self.post_url, data=post_data, headers=self.headers)
            statusCode = response.status_code
        except Exception as e:
            print('Login: login Failed, e=' + e)
            statusCode = 0
            g_returnResponseText = ''
        finally:
            print('Login:  statusCode={}'.format(statusCode))
            if statusCode == 200:
                g_returnResponseText = response.text
            else:
                g_returnResponseText = ''
        return statusCode

#pip install PySocks
def setProxy():
    socks.set_default_proxy(socks.HTTP, '10.144.1.10', 8080)
    socket.socket = socks.socksocket

def sendOutlookEmail(receivers, title, content):
    print("sendOutlookEmail: Begin to send Email!")
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        try:
            mail = outlook.CreateItem(0)
            recip1 = mail.Recipients.Add(receivers) # 指定收件者
            subj = mail.Subject = title  # 指定邮件标题
            body = [content]
            mail.Body = "\r\n".join(body)
            try:
                mail.Send()
                print("sendOutlookEmail: Mail has been send successfully!")
            except Exception as e:
                print('sendOutlookEmail: send failed, e=' + e)
        except Exception as e:
            print('sendOutlookEmail: CreateItem failed, e=' + e)
    except Exception as e:
        print('sendOutlookEmail: Dispatch failed, e=' + e)

def reTrigger(login, failedID):
    post_data = {
        'patchPhaseSid': failedID,
        'priority': 0
    }
    login.post_url = 'http://10.159.215.231:8080/gitgerrit/patch/rerun-all'
    try:
        response = login.session.post(login.post_url, data=post_data, headers=login.headers)
        if response.status_code == 200:
            print('reTrigger: reTrigger successfully, patchPhaseSid = {}'.format(failedID))
    except Exception as e:
        print('reTrigger: reTrigger failed, e=' + e)

def checkCiFailTime(soup):
    global g_break

    try:
        labelContent = soup.find('label', class_='label label-danger')
        if labelContent is not None:
            ciFailTime = int(re.sub('\D', '', labelContent.text))
            print(f'CI fail time is {ciFailTime}.')
            if ciFailTime > 20:
                g_break = True
    except Exception as e:
        print('checkCiFailTime fail')

def checkCIStatus(soup, label, classContent, tag):
    try:
        passTag = soup.find(label, class_ = classContent)
        if passTag is not None:
            print(f'The CI status is {tag}!!!')
            return True
    except Exception as e:
        print(f'find {tag} tag fail')
    return False

def runCi(login, html):
    global g_passReason

    soup = BeautifulSoup(html, 'lxml')

    if True == checkCIStatus(soup, 'label', 'label label-success', 'PASS'):
        g_passReason = 'PASS'
        return True
    if True == checkCIStatus(soup, 'label', 'label-default', 'ABORTED'):
        g_passReason = 'ABORTED'
        return True

    if True == checkCIStatus(soup, 'label', 'label label-danger', 'FAIL'):
        checkCiFailTime(soup)
        reTrigger(login, g_ciId)
        return False
    if True == checkCIStatus(soup, 'div',   'progress-bar',       'running'):
        return False
    if True == checkCIStatus(soup, 'label', 'label label-info',   'ready'):
        return False
    return False

def getEmailAddr():
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        return outlook.Session.Accounts.Item(1).SmtpAddress
    except Exception as e:
        return ''

def main():
    global g_ciId
    global g_ciWebPage
    global g_login
    loopTime = 10
    emailAddr = getEmailAddr()

    login = Login()

    try:
        username = input('Please input Nokia username:')
        password = getpass.getpass('Please input Nokia password:')
        g_ciId = input('Please input CI phaseSid ID(such as 74325):')
        g_ciWebPage = 'http://10.159.215.231:8080/gitgerrit/patch/detail?phaseSid=' + g_ciId

        statusCode = login.login(username = username, password = password)
    except Exception as e:
        print('Main: call login failed, e='+e)
        exit(0)

    while(False == g_break):
        localtime = time.asctime(time.localtime(time.time()))
        print(f'Main: Checking start at {localtime}:')
        statusCode = 0
        try:
            html = requests.get(login.logined_url)
            g_returnResponseText = html.text
            try:
                status = runCi(login, g_returnResponseText)
                if True == status:
                    sendOutlookEmail(emailAddr, f'CI status is {g_passReason}!', g_ciWebPage)
                    break;
                print(f'Main: waiting for {loopTime} seconds ......')
                print('')
                time.sleep(loopTime)
            except Exception as e:
                print('Main: call runCi failed, e={}'.format(e))
                time.sleep(loopTime)
        except Exception as e:
            print('Main: call requests failed, e={}'.format(e))
            time.sleep(loopTime)

    if True == g_break:
        sendOutlookEmail(emailAddr, 'Retrigger CI count is over 25 times, please check it!', g_ciWebPage)

if __name__ == "__main__":
    setProxy()
    main()
