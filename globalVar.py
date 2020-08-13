
def initConfigFileDict():
    global g_ConfigFileDict
    g_ConfigFileDict = {}

def setConfigFileValue(name, value):
    global g_ConfigFileDict
    g_ConfigFileDict[name] = value

def getConfigFileValue(name, defValue=None):
    global g_ConfigFileDict
    try:
        return g_ConfigFileDict[name]
    except KeyError:
        return defValue

def setLogFile(logFile):
    global g_logFile
    g_logFile = logFile

def getLogFile():
    global g_logFile
    return g_logFile

def setConFileDebug(debugSwitch):
    global g_debugConFile
    g_debugConFile = debugSwitch

def getConFileDebug():
    return g_debugConFile
