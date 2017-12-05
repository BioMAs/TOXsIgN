#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------
#
#  Project : TOXsIgN
#  GenOuest / IRSET
#  35000 Rennes
#  France
#
# -----------------------------------------------------------
#  Created on 1 jul. 2016
#  Author: tdarde <thomas.darde@inria.fr>
#  Last Update : 20 jul. 2016

########################################################################
#                                                                      #
#  Format CheBi ontology file result from Fred TCL script              #
#  Require :                                                           #
#   chebi.obo                                                          #
#   chebi.obo.tab                                                      #
#                                                                      #
########################################################################

########################################################################
#                                Import                                #
########################################################################
from libchebipy import *
import ast

########################################################################
#                                Main Function                         #
########################################################################
def getTerm(stream):
  block = []
  for line in stream:
    if line.strip() == "[Term]" or line.strip() == "[Typedef]":
      break
    else:
      if line.strip() != "":
        block.append(line.strip())

  return block

def parseTagValue(term):
  data = {}
  for line in term:
    tag = line.split(': ',1)[0]
    value = line.split(': ',1)[1]
    if not data.has_key(tag):
      data[tag] = []

    data[tag].append(value)

  return data


oboFile = open('/Users/tdarde/Documents/CloudStation/Projets/TOXsIgN/Ontology/chebi_core.obo.txt','r')

#declare a blank dictionary
#keys are the goids
terms = {}

#skip the file header lines
getTerm(oboFile)

#infinite loop to go through the obo file.
#Breaks when the term returned is empty, indicating end of file
while 1:
  #get the term using the two parsing functions
  term = parseTagValue(getTerm(oboFile))
  if len(term) != 0:
    termID = term['id'][0]
    if 'CHEBI' in termID :
        print termID
        entity = ChebiEntity(termID)
        database = entity.get_database_accessions()
        for i in database :
            test = str(i)
            CAS_nb = 'NA'
            dict = ast.literal_eval(test)
            if dict['_DatabaseAccession__typ'] == "CAS Registry Number":
                CAS_nb = dict['_DatabaseAccession__accession_number']
                terms[termID] = CAS_nb

      #for every parent term, add this current term as children
      #for termParent in termParents:
      #  if not terms.has_key(termParent):
      #    terms[termParent] = {'p':[],'c':[]}
      #  terms[termParent]['c'].append(termID)
  else:
    break
print terms
tabOboChebi = open('/Users/tdarde/Desktop/chebi.tab','r')
print "Create dico Name"
dName = {}
for lines in tabOboChebi.readlines():
    ID = lines.split('\t')[0]
    Name = lines.split('\t')[2].rstrip()
    dName[ID] = Name
tabOboChebi.close

tabOboChebi = open('/Users/tdarde/Desktop/chebi.tab','r')
finaltabObo = open('/Users/tdarde/Desktop/chemical.tab','a')

#Create dico Name

for lines in tabOboChebi.readlines():
    ID = lines.split('\t')[0]

    dbase = 'chebi'
    Name = lines.split('\t')[2]
    synonyms = lines.split('\t')[3]
    direct_parent = lines.split('\t')[4]
    aparent = lines.split('\t')[5].rstrip()
    all_parent = lines.split('\t')[5].split("|")
    NewName = Name +" CAS:NA"
    if ID in terms :
        NewName = Name +" CAS:"+terms[ID]
    all_parentName=[]
    for i in all_parent:
        if i.rstrip() in dName :
            pName = dName[i.rstrip()]
            all_parentName.append(pName)
        
    allparent = "|".join(all_parentName)
    txt = ID+"\t"+dbase+"\t"+NewName+"\t"+synonyms+"\t"+direct_parent+"\t"+aparent+"\t"+allparent+"\n"
    finaltabObo.write(txt)
    
print len(terms)
print len(dName)
    
