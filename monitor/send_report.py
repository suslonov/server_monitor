#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import shutil
import subprocess

MAIL = '../parameters/mail.sec'
PARAMETERS = "../parameters/checks.sec"

def send_mail(mail_parameters, date_now, server, my_msg, attachments):
   
    msg = MIMEMultipart() 
    msg['From'] = mail_parameters["Sender"]
    msg['To'] = "".join([r + "; " for r in mail_parameters["Recipients"]])
    msg['Subject'] = "Server monitoring_" + str(date_now) + " (UTC)"

    body = server + " " + str(date_now) + " (UTC) " + my_msg
    msg.attach(MIMEText(body, 'plain'))

    for a in attachments:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachments[a])
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', "attachment; filename=" + a + ".csv;")
        msg.attach(part)    

    message = msg.as_string()
    smtp = smtplib.SMTP(mail_parameters["SMTP"], mail_parameters["Port"])
    smtp.starttls()
    smtp.login(mail_parameters["Sender"], mail_parameters["Password"]) # less secure aps should be ON
    smtp.sendmail(mail_parameters["Sender"], mail_parameters["Recipients"], message)
    smtp.quit()

def sql_check(parameters):
    import MySQLdb
    db = MySQLdb.connect(host = parameters["host"],
                         user = parameters["user"],
                         passwd = parameters["passwd"],
                         db = parameters["database"])
    cursor = db.cursor()
    i = cursor.execute(parameters["sql"])
    return i < parameters["limit"]

def drive_space_check(parameters):
    return shutil.disk_usage(parameters["path"]).free < parameters["limit"] * 1e9

def monthly_check(parameters, date_now):
    return (date_now.day == 0) and (date_now.hour == 0 or not "hour" in parameters) and (date_now.minute == 0 or not "minute" in parameters)

def raid_check(parameters):
    result = subprocess.run(["bash"] + parameters["shell"].split(), stdout=subprocess.PIPE)

    if result.stdout.lower().find(b"disabled") >= 0:
        return True
    elif result.stdout.lower().find(b"critical") >= 0:
        return True
    return False

def main():
    with open(PARAMETERS, 'r') as f:
        params = json.load(f)
    with open(MAIL, 'r') as f:
        mail_params = json.load(f)
        
    date_now = datetime.utcnow().replace(microsecond=0)
    server = list(params.keys())[0]
    for k in params[server]:
        if params[server][k]["check"] == "sql":
            if sql_check(params[server][k]):
                send_mail(mail_params, date_now, server, k + " " + params[server][k]["message"], [])
        elif params[server][k]["check"] == "space":
            if drive_space_check(params[server][k]):
                send_mail(mail_params, date_now, server, k + " " + params[server][k]["message"], [])
        elif params[server][k]["check"] == "raid":
            if raid_check(params[server][k]):
                send_mail(mail_params, date_now, server, k + " " + params[server][k]["message"], [])
        elif params[server][k]["check"] == "monthly":
            if monthly_check(params[server][k], date_now):
                send_mail(mail_params, date_now, server, k + " " + params[server][k]["message"], [])

if __name__ == '__main__':
    main()
