#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 6 dec. 2016

@author: tdarde
'''



"""
    Create Toxsign database.
    Allow to create projects,studies,conditions and signatures collection.
    Also give the opportunity to fill database with ChemPSy Data
    Upload GeneInfo,HomoloGenes and all_info files data
    Use tox_core.py file  
"""

__version__ = "0.0.5"

import argparse
import sys
import datetime
import time
from hashlib import sha1
from random import randint
import bcrypt
import ConfigParser, os
from hashlib import sha1
from pymongo import MongoClient
import elasticsearch
import copy
import json
import logging




config = ConfigParser.ConfigParser()
config.readfp(open('../tox_install.ini'))

mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]
drugmatrix_path = config.get('setup','tggatehuman_path')
all_geneFile = open(drugmatrix_path+'/all_genes.txt','r')

lId = []
for idline in all_geneFile.readlines():
    IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
    lId.append(IDs.split('\t')[0])
    lId = list(set(lId))
all_geneFile.close()
dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
lresult = {}

for i in dataset_in_db:
    lresult[i['GeneID']]=[i['Symbol'],i['HID']]
    #Create 4 columns signature file
check_files = open(drugmatrix_path+'/all_genes_converted.txt','a')
for ids in lId :
    if ids in lresult :
        check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
    else :
        check_files.write(ids+'\t'+'NA\tNA'+'\t'+'\t0\n')                
check_files.close()


