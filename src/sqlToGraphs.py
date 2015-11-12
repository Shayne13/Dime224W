#!/usr/bin/python
# -*- coding: utf-8 -*-

import snap
import sqlite3 as lite
import sys

db_name = 'master.db'
output_graph_prefix = 'master_edge_list_'
output_graph_extension = '.graph'
contributor_mapping_file_name = 'contributor_mapping.txt'
recipient_mapping_file_name = 'recipient_mapping.txt'
query = 'SELECT * from Transactions'
contributorMapping = {}
recipientMapping = {}
transactionIndices = {'year': 0, 'tid': 1, 'ttid': 2, 'amount': 3, 'date': 4, 'cid': 5, 'rid': 6, 'seat': 7}

def getValue(transaction, key):
  return transaction[transactionIndices[key]]

def getContributorNodeID(transaction):
  return contributorMapping[getValue(transaction, 'cid')]

def getRecipientNodeID(transaction):
  return recipientMapping[getValue(transaction, 'year')][getValue(transaction, 'rid')][getValue(transaction, 'seat')]

def outputFileName(year):
  return output_graph_prefix + str(year) + output_graph_extension

def createAndSaveGraph(transactions, year): 
  G = snap.TNEANet.New()

  intAttributes = ['year', 'amount']
  stringAttributes = ['tid', 'ttid', 'date', 'rid', 'seat']
  for intAttribute in intAttributes:
    G.AddIntAttrE(intAttribute)
  for stringAttribute in stringAttributes:
    G.AddStrAttrE(stringAttribute)

  for transaction in transactions:
    cnodeid = getContributorNodeID(transaction)
    rnodeid = getRecipientNodeID(transaction)
    if not G.IsNode(cnodeid):
      G.AddNode(cnodeid)
    if not G.IsNode(rnodeid):
      G.AddNode(rnodeid)
    edgeid = G.AddEdge(cnodeid, rnodeid)
    for intAttribute in intAttributes:
      G.AddIntAttrDatE(edgeid, getValue(transaction, intAttribute), intAttribute)
    for stringAttribute in stringAttributes:
      G.AddStrAttrDatE(edgeid, getValue(transaction, stringAttribute), stringAttribute)    
  FOut = snap.TFOut(outputFileName(year))
  G.Save(FOut)
  FOut.Flush()


def createTransactionsDictionary(transactions):
  transactionsDictionary = {}

  for transaction in transactions:
    year = getValue(transaction, 'year')
    if year not in transactionsDictionary:
      transactionsDictionary[year] = []
    transactionsDictionary[year].append(transaction)

  return transactionsDictionary

def createContributorMapping(transactions):
  f = open(contributor_mapping_file_name,'w+')
  cnodeid = 1
  for transaction in transactions:
    cid = getValue(transaction, 'cid')
    if cid in contributorMapping:
      continue
    contributorMapping[cid] = cnodeid
    f.write(str(cnodeid) +  " " + str(cid) + "\n")
    cnodeid += 2 # contributors get odd ids
  f.close()

def createRecipientMapping(transactions):
  f = open(recipient_mapping_file_name,'w+')
  rnodeid = 0
  for transaction in transactions:
    year = getValue(transaction, 'year')
    rid = getValue(transaction, 'rid')
    seat = getValue(transaction, 'seat')
    if year not in recipientMapping:
      recipientMapping[year] = {}
    if rid not in recipientMapping[year]:
      recipientMapping[year][rid] = {}
    if seat in recipientMapping[year][rid]:
      continue
    recipientMapping[year][rid][seat] = rnodeid
    f.write(str(rnodeid) + " " + str(year) + " " + str(rid) + " " + str(seat) + "\n")
    rnodeid += 2 # recipients get even ids
  f.close() 

con = lite.connect(db_name)
with con:
    cur = con.cursor()       
    cur.execute(query)

    transactions = cur.fetchall()
    createContributorMapping(transactions)
    createRecipientMapping(transactions)

    transactionsDictionary = createTransactionsDictionary(transactions)
    for year in transactionsDictionary:
      createAndSaveGraph(transactionsDictionary[year], year)
