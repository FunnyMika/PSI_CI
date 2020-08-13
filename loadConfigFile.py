import sys
import configparser
import os
import globalVar as gl

def loadConfigFile():
    logFile = 0
    if 0 == gl.getConFileDebug():
        conFileName = os.path.dirname(os.path.realpath(sys.executable)) + '\config.ini'
        logFile = os.path.dirname(os.path.realpath(sys.executable)) + '\log.txt'
    else:
        conFileName = os.path.dirname(os.path.abspath('.')) + '\config.ini'
        logFile  = os.path.dirname(os.path.abspath('.')) + '\log.txt'

    gl.setLogFile(logFile)

    cf = configparser.ConfigParser()
    cf.read(conFileName)
    #print('debug='+str(gl.getConFileDebug()))

    gl.initConfigFileDict()
    gl.setConfigFileValue('computerLoginName', cf.get("User", "computerLoginName")) # Nokia登录名
    gl.setConfigFileValue('computerLoginPassword', cf.get("User", "computerLoginPassword")) # Nokia登录密码
    gl.setConfigFileValue('checkingInterval', cf.get("User", "checkingInterval"))  # 检查时间间隔，单位为秒
    #gl.setConfigFileValue('checkingCount', cf.get("User", "checkingCount")) # 检查次数
    gl.setConfigFileValue('isSendEmail', cf.get("Email", "isSendEmail")) # retrigger多次后是否发送邮件通知
    gl.setConfigFileValue('failThreshold', cf.get("Email", "failThreshold"))# 超过几次可以发送邮件
    gl.setConfigFileValue('receivers', cf.get("Email", "receivers")) # 接收人邮箱
