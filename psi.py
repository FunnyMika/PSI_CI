import requests
from lxml import etree
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import socks  #set proxy
import socket #set proxy

import globalVar as gl
from outlookSendMail import sendOutlookEmail
from loadConfigFile import  loadConfigFile

class Login(object):
    def __init__(self):
        self.headers = {
            'Referer': 'http://10.159.215.231:8080/gitgerrit/changes?project=MN/LTE/UPLANE-MAC-PS-TDD/tddps&owner=ltemac',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'Host': '10.159.215.231:8080',
            'Connection':'keep-alive'
        }
        self.login_url = 'http://10.159.215.231:8080/login'
        self.post_url = 'http://10.159.215.231:8080/do-login'
        self.logined_url = 'http://10.159.215.231:8080/gitgerrit/changes?project=MN/LTE/UPLANE-MAC-PS-TDD/tddps&owner=ltemac'
        self.session = requests.Session()

    def login(self, username, password):
        post_data = {
            'referer': 'http://10.159.215.231:8080/gitgerrit/changes?project=MN/LTE/UPLANE-MAC-PS-TDD/tddps&owner=ltemac',
            'id': username,
            'password': password
        }

        global g_returnResponseText
        statusCode = 0

        try:
            writeLog('Login: Begin to post web')
            response = self.session.post(self.post_url, data=post_data, headers=self.headers)
            statusCode = response.status_code
        except Exception as e:
            writeLog('Login: login Failed, e=' + e)
            statusCode = 0
            g_returnResponseText = ''
        finally:
            #writeLog('Login:  statusCode={}'.format(statusCode))
            if statusCode == 200:
                g_returnResponseText = response.text
                writeLog('Login: login CI web successfully!')
            else:
                g_returnResponseText = ''
                writeLog(f'Login: login CI web failed, statusCode={statusCode}')
        return statusCode

MAX_CI_RECORD_COUNT = 15
g_returnResponseText = ''
g_failBranchDir = {}
g_BranchFailOver25Value = pd.Series(0, index = ['trunk'])

#Retrigger对应页面所有FAIL的job
def reTrigger(login, failedID):
    post_data = {
        'patchPhaseSid': failedID,
        'priority': 0
    }
    login.post_url = 'http://10.159.215.231:8080/gitgerrit/patch/rerun-all'
    try:
        response = login.session.post(login.post_url, data=post_data, headers=login.headers)
        if response.status_code == 200:
            writeLog('reTrigger: reTrigger successfully, patchPhaseSid = {}'.format(failedID))
    except Exception as e:
        writeLog('reTrigger: reTrigger failed, e=' + e)
    #print('ReTrigger successfully, patchPhaseSid = {}'.format(failedID) + '\r\n')

#找到第一次FAIL的PSI/CPI branch
def processCiForLTEMAC(login, html):
    soup = BeautifulSoup(html, 'lxml')
    global g_failBranchDir
    recordCnt = 0
    try:
        branchList = []
        for tr in soup.find_all(name='tr'):
            jobFailCount = 0
            branchName = ''
            sackVersion = ''
            runID = 0
            ciFailCount = 0
            try:
                for td in tr.find_all(name='td'):
                    # 获得一个PSI链接ID，比如/gitgerrit/patch/detail?phaseSid=60511里的60511
                    try:
                        idLink = td.find('a', href=re.compile('^(/gitgerrit/patch/detail)+'))
                        if idLink is not None:
                            #print(idLink)
                            sackVersion = idLink.string.strip()
                            if ('FEATURE:IN PS adaptation' in sackVersion) or ('FEATURE:IN cpi adaptation' in sackVersion):
                            #if ('FEATURE:IN SACK adaptation' in sackVersion):
                                idLinkHref = idLink.attrs['href']
                                totalLen = len(idLinkHref)
                                constLen = len('/gitgerrit/patch/detail?phaseSid=')
                                runID = idLinkHref[constLen:totalLen]
                                #print(runID)
                    except Exception as e:
                        writeLog('processCiForLTEMAC: 1111 e= ' + e)

                    #获得CI fail的次数
                    try:
                        ciRunCountStr = td.find('label', title='Max Run Counts')
                        if ciRunCountStr is not None:
                            ciFailCount = int(ciRunCountStr.string.strip())
                    except Exception as e:
                        writeLog('processCiForLTEMAC: find CI run count fail! e= ' + e)

                    # 获得branch名字
                    try:
                        # link3 = td.find('a', href=re.compile('^(/gitgerrit/changes?project=MN/LTE/UPLANE-MAC-PS-TDD/tddps&branch)+'))
                        branchLink = td.find('a', href=re.compile('^(/gitgerrit/changes)+'))
                        if branchLink is not None:
                            #print(branchLink)
                            linkContext = branchLink.string.strip()
                            #writeLog(linkContext)
                            if ('LTEMAC' not in linkContext) and (int(runID) > 0):
                                branchName = linkContext
                    except Exception as e:
                        writeLog('processCiForLTEMAC: 2222 e= ' + e)

                    #把正在run的branch加入list，后面相同的branch名字不再检查
                    try:
                        procBar = td.find('div', title='progress-bar progress-bar-warning')
                        if (procBar is not None) and (branchName not in branchList):
                            branchList.append(branchName)
                            writeLog('processCiForLTEMAC: Running: ' + sackVersion)
                    except Exception as e:
                        writeLog('processCiForLTEMAC: find running branch fail! e= ' + e)

                    # 获得一个PSI里FAIL的job数量
                    if (int(runID) > 0):
                        try:
                            labelContent = td.find('label')
                            if labelContent is not None:
                                if 'FAIL' in labelContent.string:
                                    recordCnt = recordCnt + 1
                                    jobFailCount = int(re.sub('\D', '', labelContent.text))
                                elif ('PASS' in labelContent.string) or ('ABORTED' in labelContent.string):
                                    g_failBranchDir[branchName] = 0
                                    recordCnt += 1
                                    # 第一次检查到PASS，则把这个branch加入列表，后面的这个branch则不再检查，无论PASS或者FAIL
                                    if (branchName not in branchList):
                                        branchList.append(branchName)
                                        writeLog('processCiForLTEMAC: PASS: ' + sackVersion)
                        except Exception as e:
                            writeLog('processCiForLTEMAC: 3333 e= ' + e)

                    # retrigger （fail job < 6次）的PSI/CPI
                    try:
                        btn = td.find('button')
                        if btn is not None:
                            #（1）有Re-Trigger按钮。（2）第一次遍历到这个branch
                            if ('Re-Trigger' in btn.string) and (jobFailCount > 0) and (branchName not in branchList):
                                branchList.append(branchName)

                                if branchName not in g_failBranchDir.keys():
                                    g_failBranchDir[branchName] = 1
                                else:
                                    g_failBranchDir[branchName] = g_failBranchDir[branchName] + 1

                                failContent = btn.string + ' {}'.format(sackVersion) + ' for {}'.format(branchName) + \
                                      ', FAIL({})'.format(jobFailCount)
                                writeLog(' ')
                                writeLog('processCiForLTEMAC: FAIL: failContent='+failContent)
                                #fail的job数量小于12，而且CI跑的次数小于15次，则自动retrigger job；否则说明fail的job太多，需要手动查看环境问题
                                if (jobFailCount < 12) and (ciFailCount < 15):
                                    reTrigger(login, runID)
                                    if (0 == (g_failBranchDir[branchName] % int(gl.getConfigFileValue('failThreshold')))) and \
                                        (1 == int(gl.getConfigFileValue('isSendEmail'))):
                                        mailTitle = 'Fail time {}: '.format(g_failBranchDir[branchName]) + sackVersion
                                        mailContent = failContent + '\r\n' + '\r\n' + 'http://10.159.215.231:8080/gitgerrit/patch/detail?phaseSid={}'.format(runID)
                                        sendOutlookEmail(gl.getConfigFileValue('receivers'), mailTitle, mailContent)
                                else:
                                    g_BranchFailOver25Value[branchName] = g_BranchFailOver25Value[branchName] + 1
                                    if((1 == g_BranchFailOver25Value[branchName]) or ( 0 == (g_BranchFailOver25Value[branchName] % 200))) and \
                                        (1 == int(gl.getConfigFileValue('isSendEmail'))):
                                        mailTitle = 'Please retrigger manually: ' + sackVersion
                                        mailContent = failContent + '\r\n' + '\r\n' + 'http://10.159.215.231:8080/gitgerrit/patch/detail?phaseSid={}'.format(runID)
                                        sendOutlookEmail(gl.getConfigFileValue('receivers'), mailTitle, mailContent)
                                writeLog(' ')
                                time.sleep(1)
                    except Exception as e:
                        writeLog('processCiForLTEMAC: 4444 e= ' + e)
            except Exception as e:
                writeLog('processCiForLTEMAC: 5555 e= ' + e)
    except Exception as e:
        writeLog('processCiForLTEMAC: 6666 e= ' + e)

    if (0 == recordCnt):
        writeLog(html)
    #for i in range(0, len(branchList)):
    #    print(branchList[i] + ',', end='')
    #print()

#pip install PySocks
def setProxy():
    socks.set_default_proxy(socks.HTTP, '10.144.1.10', 8080)
    socket.socket = socks.socksocket

def writeLog(logContent):
    print(logContent)
    try:
        with open(gl.getLogFile(), "a", encoding="utf-8") as f2:
            f2.writelines(logContent+'\n')
    except Exception as e:
        print('writeLog: write file {} failed!'.format(gl.getLogFile()))

def getBranch(html):
    soup = BeautifulSoup(html, 'lxml')
    try:
        branches = soup.find(class_ = 'col-md-5 column btn-group')
        try:
            for branch in branches.find_all(class_ = 'btn btn-default'):
                if branch.string not in g_BranchFailOver25Value:
                    g_BranchFailOver25Value[branch.string] = 0
            #writeLog('BranchList:')
            #for branch, value in g_BranchFailOver25Value.items():
                #writeLog(branch+'    '+str(value))
        except Exception as e:
            writeLog('getBranch: find btn btn-default fail, e= ' + e)
    except Exception as e:
        writeLog('getBranch: find ol-md-5 column btn-group fail, e= ' + e)

def main():
    login = Login()

    loopTime = int(gl.getConfigFileValue('checkingInterval'))

    isBranchNameRead = False

    try:
        computerLoginName = gl.getConfigFileValue('computerLoginName')
        computerLoginPassword = gl.getConfigFileValue('computerLoginPassword')
        statusCode = login.login(username = computerLoginName, password = computerLoginPassword)
    except Exception as e:
        writeLog('Main: call login failed, e='+e)
        exit(0)

    #for i in range(0, int(gl.getConfigFileValue('checkingCount'))):
    while(1):
        localtime = time.asctime(time.localtime(time.time()))
        writeLog(f'Main: Searching CI information start at {localtime}:')
        statusCode = 0
        try:
            #writeLog('Main: call requests')
            html = requests.get(login.logined_url)
            g_returnResponseText = html.text
            try:
                if False == isBranchNameRead:
                    try:
                        writeLog('Main: Begin to get branch list')
                        getBranch(g_returnResponseText)
                        isBranchNameRead = True
                    except Exception as e:
                        writeLog('Main: call getBranch failed, e={}'.format(e))
                writeLog('Main: Begin to call processCiForLTEMAC')
                processCiForLTEMAC(login, g_returnResponseText)
                writeLog('Main: End to call processCiForLTEMAC')
                # processCiForLTEMAC(login, html)
            except Exception as e:
                writeLog('Main: call processCiForLTEMAC failed, e={}'.format(e))
        except Exception as e:
            writeLog('Main: call requests failed, e={}, call login again!'.format(e))
            try:
                statusCode = login.login(username=computerLoginName,
                                         password=computerLoginPassword)
            except Exception as e:
                writeLog('Main: call login failed for requests, e=' + e)
        finally:
            writeLog('Main: Searching CI information end!')
            writeLog('\n')
            time.sleep(loopTime)

if __name__ == "__main__":
    gl.setConFileDebug(0)
    setProxy()
    loadConfigFile()
    main()
