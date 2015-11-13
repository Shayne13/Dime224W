#!/usr/bin/python


import sys, csv, re, os, time
import sqlite3 as sql
from itertools import chain

csv_dir = 'Data/CSVs/'
db_dir = 'Data/DBs/'
csv_1982 = csv_dir + 'contribDB_1982.csv'
recipient_path = csv_dir + 'candidate_cfscores_st_fed_1979_2012.csv'
contributors_path = csv_dir + 'contributor_cfscores_st_fed_1979_2012.csv'

def loadDBForCycle(cycle):
    csvName = 'Data/CSVs/contribDB_%d.csv' % cycle
    dbName = db_dir + str(cycle) + '.db'
    loadTransactionFile(dbName, csvName, cycle)

def loadTransactionFile(dbName, csvName, year):
    print 'Loading Transactions_{0} into Table:'.format(year)
    start = time.time()
    extractors = [0, 1, 2, 3, 4, 5, 13, 27, 28, 29, 33, 34, 36, 37]
    transforms = [int, str, str, strToFltToInt, str, strToFltToInt, indiv, str, party, candOrComm, str, str, safeFloat, safeFloat]
    initTransactionsTable(dbName)

    with open(csvName, 'r') as f:
        reader = csv.reader(f)
        reader.next() # skip column headers
        for i, block in enumerate(generateChunk(reader, extractors, transforms)):
            commitTransBlock(dbName, block)

    print 'Time taken: ' + str(time.time() - start)

def loadRecipients(dbNames, filepath):
    print '------------- Loading Recipients Tables -------------'
    start = time.time()
    extractors = [0, 7, 10, 12, 13, 14, 15, 16, 22, 23, 39, 46, 47, 61, 62, 63, 64, 65]
    transforms = [int, str, party, str, str, incumb, float, float, int, gender, safeInt, winner, safeFloat, safeFloat, safeFloat, candStatus, int, candOrComm]
    observedKeys = set()

    for db in dbNames:
        initRecipientTable(db)

    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        reader.next() # skip column headers
        for i, block in enumerate(generateChunk(reader, extractors, transforms)):
            newBlock = extractDuplicateRecipients(block, observedKeys)
            for db in dbNames:
                commitRecipBlock(db, newBlock)

    print 'Time taken: ' + str(time.time() - start)

def loadContributors(dbNames, filepath):
    print '------------- Loading Contributors Tables -------------'
    start = time.time()
    extractors = [0, 1, 2, 3]
    transforms = [int, indiv, str, safeFloat]

    for db in dbNames:
        initContributorsTable(db)
    reader = csv.reader(open(filepath, 'rb'))
    reader.next() # skip column headers
    for i, block in enumerate(generateChunk(reader, extractors, transforms)):
        for db in dbNames:
            commitContribBlock(db, block)

    print 'Time taken: ' + str(time.time() - start)

# Ensures that all recipients have unique (year, rid, seat) keys
# and that only the first row is taken.
def extractDuplicateRecipients(block, observedKeys):
    newBlock = []
    for l in block:
        if ((l[0], l[1], l[3]) not in observedKeys):
            newBlock.append(l)
            observedKeys.add((l[0], l[1], l[3]))
    return newBlock

# ----- Column Transformation Functions -----

def getTransID(code):
    fullID = code.split(':')
    if (fullID[0] == "indv"):
        return -int(fullID[2])
    else:
        return int(fullID[2])

def strToFltToInt(num):
    if (num == ''): return None
    return int(float(num))

def safeFloat(num):
    if (num == ''): return None
    return float(num)

def getRecipientInfo(code):
    if (code == ""): return 0 # Return 0 if no recipient ID available
    if (code[0:4] == "cand"): return int(re.findall(r'\d+', code)[0])
    else: return -int(re.findall(r'\d+', code)[0]) # Negative recipient ID if not 'candidate'

def indiv(code):
    if (code == 'I'): return 1
    elif (code == 'C'): return 0
    else: return None

def safeInt(num):
    if (num == ''): return None
    return int(num)

def winner(code):
    if (code == 'L'): return 0
    elif (code == 'W'): return 1
    else: return None

def party(code):
    try:
        intCode = int(code)
        if intCode == 100:
            return 1
        elif intCode == 200:
            return 2
        else:
            return 3
    except:
        return 3

def incumb(code):
    if (code == 'O'): return 0
    elif (code == 'I'): return 1
    elif (code == 'C'): return 2
    else: return None

def gender(code):
    if (code == 'F'): return 1
    elif (code == 'M'): return 0
    else: return None # '' or 'U'

def candStatus(code):
    if (code == 'C'): return 1
    elif (code == 'F'): return 2
    elif (code == 'N'): return 3
    elif (code == 'P'): return 4
    else: return None

def candOrComm(code):
    if (code.lower() == 'comm'): return 0
    elif (code.lower() == 'cand'): return 1
    else: return None

# ----- Block Commit Functions -----

def commitContribBlock(dbName, block):

    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.executemany("INSERT INTO Contributors VALUES(?,?,?,?)", block)

        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close()

def commitTransBlock(dbName, block):

    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.executemany("INSERT INTO Transactions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", block)
        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close()

def commitRecipBlock(dbName, block):

    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.executemany("INSERT INTO Recipients VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", block)

        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close()

# Takes a CSV reader, the column indexes we are interested in, and the
# function transformations for each of those indexes, and returns a
# list of tuples, corresponding to the list of processed rows for our sql table.
def generateChunk(reader, extractors, transforms, chunksize=20000):
    chunk = []
    for i, line in enumerate(reader):
        if (i % chunksize == 0 and i > 0):
            yield chunk
            del chunk[:]
        # extracts columns corresponding to 'extractors', then applies 'transforms' element-wise:
        try:
            processedLine = tuple(map(lambda f,d: f(d), transforms, map(line.__getitem__, extractors)))
        except:
            print 'line processing failure:'
            raise ValueError(line)
        # flattens EG: (1, 2, 3, (4, 5), 6) --> (1, 2, 3, 4, 5, 6):
        chunk.append(tuple(chain(*(i if isinstance(i, tuple) else (i,) for i in processedLine))))
    yield chunk

# ----- Table Init Functions -----

# Initializes a Transaction table for a particular year:
# Columns: [0, 1, 2, 3, 4, 5, 13, 27, 28, 29, 33, 34, 36, 37]
def initTransactionsTable(dbName):
    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.execute("DROP TABLE IF EXISTS Transactions")
        cur.executescript("""
        CREATE TABLE Transactions(
            year INTEGER,
            tid TEXT,
            ttid VARCHAR(4),
            amount INTEGER,
            date VARCHAR(10),
            cid INTEGER,
            indiv INTEGER,
            rid TEXT,
            party INTEGER,
            candOrComm INTEGER,
            district VARCHAR(8),
            seat TEXT,
            cfscore REAL,
            cfs REAL,
            PRIMARY KEY(year, tid),
            FOREIGN KEY(cid) REFERENCES Contributors(cid),
            FOREIGN KEY(rid) REFERENCES Recipients(rid),
            FOREIGN KEY(seat) REFERENCES Recipients(seat)
        );""")

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close()

# Initializes the Contributors table:
# Columns: [0, 1, 2]
def initContributorsTable(dbName):
    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.execute("DROP TABLE IF EXISTS Contributors")
        cur.executescript("""
            CREATE TABLE Contributors(
              cid INTEGER PRIMARY KEY,
              indiv INTEGER,
              state VARCHAR(4),
              cfscore REAL
            );""")

        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close()

# Columns: [0, 7, 10, 12, 13, 14, 15, 16, 22, 23, 39, 46, 47, 61, 62, 63, 64, 65]
# 39-ran primary  , 46 winner, 47 district partisanship, 61 in district donations
def initRecipientTable(dbName):
    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()

        cur.execute("DROP TABLE IF EXISTS Recipients")
        cur.executescript("""
            CREATE TABLE Recipients(
              year INTEGER,
              rid TEXT,
              party INTEGER,
              seat TEXT,
              district VARCHAR(8),
              incumb INTEGER,
              cfs REAL,
              cfsdyn REAL,
              numgivers INTEGER,
              gender INTEGER,
              didprimary INTEGER,
              winner INTEGER,
              partisanship REAL,
              indistrict REAL,
              instate REAL,
              candstatus INTEGER,
              fecyear INTEGER,
              candorcomm INTEGER,
              PRIMARY KEY(year, rid, seat)
            );""")
        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:
        if con: con.close()

if __name__ == '__main__':
    dbNames = [db_dir + str(cycle) + '.db' for cycle in range(1980, 2014, 2)]
    #loadRecipients(dbNames, recipient_path)
    #loadContributors(dbNames, contributors_path)
    for cycle in range(1980, 1990, 2):
        loadDBForCycle(cycle)

# ----- USEFUL CODE FOR DEBUGGING: -----

# lst = []
# extractors = [0, 7, 10, 12, 13, 14, 15, 16, 22, 23, 39, 46, 47, 61, 62, 63, 64, 65]
# transforms = [int, str, party, str, str, incumb, float, float, int, gender, safeInt, winner, safeFloat, safeFloat, safeFloat, candStatus, int, candOrComm]

# xst = map(lst.__getitem__, extractors)
# print xst

# print tuple(map(lambda f,d: f(d), transforms, xst))

# for i, f in enumerate(transforms):
#     print i, f
#     f(xst[i])
