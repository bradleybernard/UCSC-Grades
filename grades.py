# Grade script
# Created by Brad Bernard
# Requires: bs4, twilio, requests, requests[security], pyyaml
# $ python3 grades.py CruzID GoldPass PhoneNum TermID [--no-texts]

from bs4 import BeautifulSoup
from twilio.rest import TwilioRestClient
import requests

import argparse
import sqlite3
import urllib
import time
import pprint
import os
import datetime
import yaml

# Notifications Toggle
_enable_texts   = True

# Twilio API
_twilio_account = ''
_twilio_token   = ''
_from_phone     = ''
_to_phone       = ''

# UCSC
_cruz_id        = ''
_gold_password  = '' 
_term_id        = ''
_url            = 'https://ais-cs.ucsc.edu/psc/csprd/EMPLOYEE/PSFT_CSPRD/c/SA_LEARNER_SERVICES.SSR_SSENRL_GRADE.GBL'
_terms          = {
                    '2168': 'Fall 2016',
                    '2164': 'Summer 2016',
                    '2162': 'Spring 2016',
                    '2160': 'Winter 2016',
                    '2158': 'Fall 2015',
                  }

# Sqlite3
_db_file    = ''

# Scraper
_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2633.3 Safari/537.36'

def setupDb():

    global _db_file, _cruz_id
    _db_file = '%s_grades.sqlite3' % (_cruz_id)

    new = not os.path.exists(_db_file)
    conn = sqlite3.connect(_db_file, isolation_level=None)
    cursor = conn.cursor()

    if new:
        cursor.execute(
            """CREATE TABLE `grades` (
            `id`                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            `class_name`        TEXT NOT NULL,
            `class_description` TEXT NOT NULL,
            `class_units`       TEXT NOT NULL,
            `grading`           TEXT NOT NULL,
            `grade`             TEXT NOT NULL,
            `grade_points`      TEXT NOT NULL,
            `term_id`           TEXT NOT NULL,
            `created_at`        INTEGER NOT NULL);"""
        )

        print ('Database %s setup complete.' % (_db_file))
    else:
        print ('Database %s already created.' % (_db_file))

    conn.close()

def readYaml():

    # Open Yaml config file
    with open('twilio.yaml', 'r') as file:
        data = yaml.load(file)

        # Set globals to yaml values
        global _twilio_account, _twilio_token, _from_phone

        _twilio_account = data['account']
        _twilio_token   = data['token']
        _from_phone     = data['phone']

def checkArgs():

    parser = argparse.ArgumentParser(description="Notify student on final grades in MyUCSC portal")

    # Setup required arguments
    parser.add_argument('CruzID', help='UCSC Cruz ID for Ecommons')
    parser.add_argument('GoldPass', help='UCSC Gold Password for Ecommons')
    parser.add_argument('Phone', help='Mobile phone number to receive texts', )
    parser.add_argument('TermID', help='Term ID to check grades for')
    parser.add_argument('--no-texts', help='Turn off text message notifications', action='store_true')
    args = parser.parse_args()

    # Set globals to parsed argument values
    global _cruz_id, _gold_password, _to_phone, _enable_texts, _term_id
    _cruz_id = args.CruzID
    _gold_password = args.GoldPass
    _to_phone = args.Phone
    _term_id = args.TermID

    # Disable texts if --no-texts optional arg is given
    if args.no_texts:
        _enable_texts = False

def checkChanges(row, dictionary):
    return not (
        (row[0] == dictionary['units']) 
        and (row[1] == dictionary['grading']) 
        and (row[2] == dictionary['grade']) 
        and (row[3] == dictionary['gradePoints'])
    )

def insertGrade(cursor, dictionary):
    cursor.execute('INSERT INTO grades (class_name, class_description, class_units, grading, grade, grade_points, term_id, created_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', 
        [dictionary['name'], dictionary['description'], dictionary['units'], dictionary['grading'], dictionary['grade'], dictionary['gradePoints'], _term_id, dictionary['createdAt']])

def deleteGrade(cursor, dictionary):
    cursor.execute("DELETE FROM grades WHERE class_name = :ClassName AND term_id = :TermId", {'ClassName': dictionary['name'], 'TermId': _term_id})

def createMessage(type, dictionary):
    message = '[' + type + '] '
    message += 'MyUCSC.\n'
    message += 'Class: %s\n' % (dictionary['name'])
    message += 'Grading: %s\n' % (dictionary['grading'])
    message += 'Grade: %s\n' % (dictionary['grade'])
    
    if dictionary['grading'] != 'Pass/No Pass':
        message += 'Grade points: %s\n' % (dictionary['gradePoints'])

    # message += 'Sent: %s (PST)' % (datetime.datetime.fromtimestamp(dictionary['createdAt']).strftime('%B %d, %I:%M %p'))
    return message

def main():

    # Parse and set arguments
    checkArgs()

    # Read and parse yaml config file
    readYaml()

    # Setup SQLite3 database
    setupDb()

    pp = pprint.PrettyPrinter(indent=4)
    client = TwilioRestClient(_twilio_account, _twilio_token)

    session = requests.Session()

    headers = {
        'User-Agent': _user_agent
    }

    data = {
        'userid': _cruz_id,
        'pwd': _gold_password,
        'Submit': 'Sign In',
        'timezoneOffset': '420'
    }

    print ('Logging into MyUCSC as %s.' % (_cruz_id))

    login = session.post(_url, data=data, headers=headers)
    loginHTML = BeautifulSoup(login.text, 'html.parser')

    params = {
        'ACAD_CAREER': 'UGRD',
        'INSTITUTION': 'UCSCM',
        'STRM': _term_id,
    }

    print ('Selecting grades for the %s term.' % (_terms[_term_id]))

    termSelect = session.get(_url, params=params, headers=headers)
    gradesHTML = BeautifulSoup(termSelect.text, 'html.parser')

    table = gradesHTML.select('table.PSLEVEL1GRID')[0]
    rows = table.select('tr')
    rows.pop(0)

    conn = sqlite3.connect(_db_file, isolation_level=None)
    cursor = conn.cursor()

    for row in rows:

        classDict = {
            'name':         row.select('td')[0].select('a')[0].string.strip(),
            'description':  row.select('td')[1].select('span')[0].string.strip(),
            'units':        row.select('td')[2].select('span')[0].string.strip(),
            'grading':      row.select('td')[3].select('span')[0].string.strip(),
            'grade':        row.select('td')[4].select('span')[0].string.strip(),
            'gradePoints':  row.select('td')[5].select('span')[0].string.strip(),
            'createdAt':    int(time.time()),
        }

        # print ('Class: ')
        # pp.pprint(classDict)

        cursor = cursor.execute('SELECT class_units, grading, grade, grade_points FROM grades WHERE class_name = :ClassName AND term_id = :TermId', {'ClassName': classDict['name'], 'TermId': _term_id})
        row = cursor.fetchone()

        dbExists = row is not None
        gradeExists = not (classDict['grade'] == '')
        gradeChanges = checkChanges(row, classDict)

        if gradeExists and not dbExists:
            print ('Inserting new grade for %s into database.' % (classDict['name']))

            insertGrade(cursor, classDict)

            message = createMessage('NEW', classDict)

            if _enable_texts:
                client.messages.create(to=_to_phone, from_=_from_phone, body=message)

        elif gradeExists and dbExists and gradeChanges:
            print ('Updating grade for %s in the database.' % (classDict['name']))

            deleteGrade(cursor, classDict)
            insertGrade(cursor, classDict)

            message = createMessage('UPDATED', classDict)

            if _enable_texts:
                client.messages.create(to=_to_phone, from_=_from_phone, body=message)

    conn.close()

    print ('Finished checking grades for %s.' % (_cruz_id))

if __name__ == "__main__":
    main()
