import win32com.client

def writeLog(logContent):
    print(logContent)

def sendOutlookEmail(receivers, title, content):
    writeLog("sendOutlookEmail: Begin to send Email!")
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        #print(outlook.Session.Accounts.Item(1).SmtpAddress)
        try:
            mail = outlook.CreateItem(0)
            recip1 = mail.Recipients.Add(receivers) # 指定收件者
            # recip2 = mail.Recipients.Add("67377651@qq.com")
            subj = mail.Subject = title  # 指定邮件标题
            body = [content]
            mail.Body = "\r\n".join(body)
            try:
                mail.Send()
                writeLog("sendOutlookEmail: Mail has been send successfully!")
            except Exception as e:
                writeLog('sendOutlookEmail: send failed, e=' + e)
        except Exception as e:
            writeLog('sendOutlookEmail: CreateItem failed, e=' + e)
    except Exception as e:
        writeLog('sendOutlookEmail: Dispatch failed, e=' + e)
