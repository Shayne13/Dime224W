
# coding: utf-8

# In[1]:

#!/usr/bin/python


import sys, csv, re, os, time
import sqlite3 as sql
from itertools import chain


# In[31]:

db_name = 'master.db'
csv_1982 = 'Data/contribDB_1982.csv'
recipient_path = 'Data/candidate_cfscores_st_fed_1979_2012.csv'
contributors_path = 'Data/contributor_cfscores_st_fed_1979_2012.csv'
loadAllTransactionFilesInDir(db_name, 'Data/')
loadRecipients(db_name, recipient_path)
loadContributors(db_name, contributors_path)


# In[2]:

def loadAllTransactionFilesInDir(dbName, dirpath):
    print '------------- Loading All Transaction Tables -------------'
    start = time.time()
    transFiles = [ f for f in listdir_nohidden(dirpath) if (f.split('_')[0] == "contribDB") ]
    initTransactionsTable(dbName)
    for tf in transFiles:
        loadTransactionFile(dbName, dirpath + tf, int(tf.split('_')[1][0:4]))
    print 'Total time taken: ' + str(time.time() - start) 


# In[3]:

def listdir_nohidden(path):
    for f in os.listdir(path):
        if not f.startswith('.'):
            yield f


# In[4]:

def loadTransactionFile(dbName, filepath, year):
    print 'Loading Transactions_{0} into Table:'.format(year)
    start = time.time()
    extractors = [0, 1, 2, 3, 4, 5, 27, 34]
    transforms = [int, str, str, strToFltToInt, str, strToFltToInt, str, str]
    
    reader = csv.reader(open(filepath, 'rb'))
    reader.next() # skip column headers
    for i, block in enumerate(generateChunk(reader, extractors, transforms)):
        commitTransBlock(dbName, block)
        
    print 'Time taken: ' + str(time.time() - start)


# In[5]:

def loadRecipients(dbName, filepath):
    print '------------- Loading Recipients Table -------------'
    start = time.time()
    extractors = [0, 7, 10, 12, 13, 14, 15, 16, 22, 23, 39, 46, 47, 61, 62, 63, 64, 65]
    transforms = [int, str, party, str, str, incumb, float, float, int, gender, safeInt, winner, safeFloat, safeFloat, safeFloat, candStatus, int, candOrComm]
    observedKeys = set()
    
    initRecipientTable(dbName)
    reader = csv.reader(open(filepath, 'rb'))
    reader.next() # skip column headers
    for i, block in enumerate(generateChunk(reader, extractors, transforms)):
        newBlock = extractDuplicateRecipients(block, observedKeys)
        commitRecipBlock(dbName, newBlock)
    
    print 'Time taken: ' + str(time.time() - start) 


# In[6]:

def loadContributors(dbName, filepath):
    print '------------- Loading Contributors Table -------------'
    start = time.time()
    extractors = [0, 1, 2, 3]
    transforms = [int, indiv, str, safeFloat]
    
    initContributorsTable(dbName)
    reader = csv.reader(open(filepath, 'rb'))
    reader.next() # skip column headers
    for i, block in enumerate(generateChunk(reader, extractors, transforms)):
        commitContribBlock(dbName, block)
    
    print 'Time taken: ' + str(time.time() - start) 


# In[7]:

# Ensures that all recipients have unique (year, rid, seat) keys
# and that only the first row is taken.
def extractDuplicateRecipients(block, observedKeys):
    newBlock = []
    for l in block:
        if ((l[0], l[1], l[3]) not in observedKeys):
            newBlock.append(l)
            observedKeys.add((l[0], l[1], l[3]))
    return newBlock


# In[8]:

# ----- Column Transformation Functions -----


# In[9]:

def getTransID(code):
    fullID = code.split(':')
    if (fullID[0] == "indv"):
        return -int(fullID[2])
    else:
        return int(fullID[2])


# In[10]:

def strToFltToInt(num):
    if (num == ''): return None
    return int(float(num))


# In[11]:

def safeFloat(num):
    if (num == ''): return None
    return float(num)


# In[12]:

def getRecipientInfo(code):
    if (code == ""): return 0 # Return 0 if no recipient ID available
    if (code[0:4] == "cand"): return int(re.findall(r'\d+', code)[0])
    else: return -int(re.findall(r'\d+', code)[0]) # Negative recipient ID if not 'candidate'


# In[13]:

def indiv(code):
    if (code == 'I'): return 1
    elif (code == 'C'): return 0
    else: return None


# In[14]:

def safeInt(num):
    if (num == ''): return None
    return int(num)


# In[15]:

def winner(code):
    if (code == 'L'): return 0
    elif (code == 'W'): return 1
    else: return None


# In[16]:

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


# In[17]:

def incumb(code):
    if (code == 'O'): return 0
    elif (code == 'I'): return 1
    elif (code == 'C'): return 2
    else: return None


# In[18]:

def gender(code):
    if (code == 'F'): return 1
    elif (code == 'M'): return 0
    else: return None # '' or 'U'


# In[19]:

def candStatus(code):
    if (code == 'C'): return 1
    elif (code == 'F'): return 2
    elif (code == 'N'): return 3
    elif (code == 'P'): return 4
    else: return None


# In[20]:

def candOrComm(code):
    if (code == 'comm'): return 0
    elif (code == 'cand'): return 1
    else: return None


# In[21]:

# ----- Block Commit Functions -----


# In[22]:

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


# In[23]:

def commitTransBlock(dbName, block):

    con = None
    try:
        con = sql.connect(dbName)
        cur = con.cursor()  
        
        cur.executemany("INSERT INTO Transactions VALUES(?,?,?,?,?,?,?,?)", block)
        con.commit()

    except sql.Error, e:

        if con: con.rollback()
        print "Error %s:" % e.args[0]
        sys.exit(1)

    finally:

        if con: con.close() 


# In[24]:

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


# In[25]:

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


# In[26]:

# ----- Table Init Functions -----


# In[27]:

# Initializes a Transaction table for a particular year:
# Columns: [1, 2, 3, 4, 5, 27, 34]
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
            rid TEXT,
            seat TEXT,
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


# In[28]:

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


# In[29]:

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


# In[30]:

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


# In[ ]:



