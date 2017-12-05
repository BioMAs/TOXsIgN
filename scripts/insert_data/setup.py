#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 5 dec. 2016

@author: tdarde
'''



"""
    Create Toxsign database.
    Allow to create projects,studies,conditions and signatures collection.
    Also give the opportunity to fill database with ChemPSy Data
    Upload GeneInfo,HomoloGenes and all_info files data
    Use tox_core.py file  
"""

__version__ = "0.1.8"

import toxcore_v2 as toxcore
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

"""
Create TOXsign setup log file
"""
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
file_handler = RotatingFileHandler('TOXsIgN_database_creation.log', 'a', 1000000, 1)
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
 


    


def install_toxsign():
    """
        Install TOXsIgN collection and put ChemPSy information in database
    """
    try :
        logger.info('install_toxsign')
        toxcore.createCollections()
        toxcore.createCounters()
        toxcore.insertDM()
        toxcore.insertTGGATE()
        toxcore.CreateDemoUser()
        toxcore.insertHumanTG()
    except:
        logger.error(sys.exc_info()[1])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize database content.')
    parser.add_argument('--install')
    #parser.add_argument('--pwd')
    #parser.add_argument('--email')
    args = parser.parse_args()
    
    if args.install == 'INSTALL':
        os.system('curl -XDELETE localhost:9200/toxsign')
        os.system('mongo toxsign --eval "db.dropDatabase()"')
        install_toxsign()
        
    if args.install == 'DATABASE':
        os.system('curl -XDELETE localhost:9200/toxsign')
        os.system('mongo toxsign --eval "db.dropDatabase()"')
        toxcore.createCollections()
        toxcore.createCounters()
        
    if args.install =='CHEMICAL':
        os.system('mongo toxsign --eval "db.chemical.tab.drop()"')
        toxcore.chemicalDB()
    
    if args.install == 'SIGNATURE':
        toxcore.createCounters()
        os.system('mongo toxsign --eval "db.datasets.drop()"')
        os.system('curl -XDELETE localhost:9200/toxsign')
        toxcore.insertDM()
    if args.install == 'DM':
        toxcore.insertDM()
        
    if args.install == "TGGATE":
        toxcore.insertTGGATE()
    
    if args.install == "DEMO":
        toxcore.CreateDemoUser()
    
    if args.install =="HUMAN":
        toxcore.insertHumanTG()
    
    if args.install =="ALLHUMAN":
        logger.info('ALLHUMAN')
        toxcore.otherHuman()
        
    if args.install =="INDEX":
        toxcore.indexElastic()
