#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 13 nov. 2018

@author: tdarde
'''



"""
    Update TOXsIgN ElasticSearch indexes.
"""
import argparse
import sys
import datetime
from time import *
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
import xlsxwriter
import elasticsearch
from logging.handlers import RotatingFileHandler
 
# création de l'objet logger qui va nous servir à écrire dans les logs
logger = logging.getLogger()
# on met le niveau du logger à DEBUG, comme ça il écrit tout
logger.setLevel(logging.DEBUG)
 
# création d'un formateur qui va ajouter le temps, le niveau
# de chaque message quand on écrira un message dans le log
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
# création d'un handler qui va rediriger une écriture du log vers
# un fichier en mode 'append', avec 1 backup et une taille max de 1Mo
file_handler = RotatingFileHandler('TOXsIgN_database_creation.log', 'a', 1000000000, 1)
# on lui met le niveau sur DEBUG, on lui dit qu'il doit utiliser le formateur
# créé précédement et on ajoute ce handler au logger
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
 
# création d'un second handler qui va rediriger chaque écriture de log
# sur la console
steam_handler = logging.StreamHandler()
steam_handler.setLevel(logging.DEBUG)
logger.addHandler(steam_handler)




#Functions used for data insertion
#This functions required information from config file
#By default all config information are load from ../tox_install.ini file
#To modifie information please set value in thise file
#DO NOT MODIFIE the tox_install.ini file location 
config = ConfigParser.ConfigParser()
config.readfp(open('tox_install.ini'))

mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]
es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])

def update_project_indexes(pId):
    project = db['projects'].find_one({'id' :pId})
    pid = project['id']
    stid = project['studies'].split(',')
    aid = project['assays'].split(',')
    sid = project['signatures'].split(',')

    del project['_id']
    bulk_insert = ''
    bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+proj['id']+"\" } }\n"
    bulk_insert += json.dumps(project)+"\n"
    if bulk_insert:
        es.bulk(body=bulk_insert)

    for stud in stid:
        study = db['studies'].find_one({'id' :stud})
        del study['_id']
        bulk_insert = ''
        bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+study['id']+"\" } }\n"
        bulk_insert += json.dumps(study)+"\n"
        if bulk_insert:
            es.bulk(body=bulk_insert)

    for ass in aid:
        assay = db['assays'].find_one({'id' :ass})
        del assay['_id']
        bulk_insert = ''
        bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assay['id']+"\" } }\n"
        bulk_insert += json.dumps(assay)+"\n"
        if bulk_insert:
            es.bulk(body=bulk_insert)

    for sign in sid:
        signature = db['signatures'].find_one({'id' :sign})
        del signature['_id']
        bulk_insert = ''
        bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signature['id']+"\" } }\n"
        bulk_insert += json.dumps(signature)+"\n"
        if bulk_insert:
           es.bulk(body=bulk_insert)
    return {'msg':'Project status changed : Pending --> public'}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize database content.')
    parser.add_argument('--id')
    #parser.add_argument('--pwd')
    #parser.add_argument('--email')
    args = parser.parse_args()
    update_project_indexes(args.id)