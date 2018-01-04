#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 4 Jan. 2018

@author: tdarde
'''



"""
    Use LINCs database to list all conditions available
"""

from pymongo import MongoClient
import ConfigParser
import sys


#Functions used for data insertion
#This functions required information from config file
#By default all config information are load from ../tox_install.ini file
#To modifie information please set value in thise file
#DO NOT MODIFIE the tox_install.ini file location 
config = ConfigParser.ConfigParser()
config.readfp(open('LINCS_install.ini'))



mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]


def ExtractCond(obj):
    """
        Take a dictionary object from LINCS database and determine the associated condition
        Return: String. Condition name
    """
    try:
        chem = obj['pert_desc']
        dose = str(obj['pert_dose'])
        dose_unit = obj['pert_dose_unit']
        time = str(obj['pert_time'])
        time_unit = obj['pert_time_unit']
        cell = obj['cell_id']
        cond_name = 'LINCS+'+cell+'+'+chem+'+'+dose+dose_unit+'+'+time+time_unit
        return cond_name
    except:
        print obj

def getAllIDs():
    """
        Get all sign ID of LINCS database
        Return: List of signature ids
    """
    try :
        all_signature = list(db['cpc2014'].distinct('sig_id'))
        return all_signature
    except:
        sys.exc_info()[1]


if __name__ == "__main__":
    print "RUN LINCS parser"
    dConditions = {}
    all_sign = getAllIDs()
    for sign_id in all_sign :
        obj = db['cpc2014'].find_one({'sig_id':sign_id})
        cond_name = ExtractCond(obj)
        if cond_name is None :
            print sign_id
            sys.exit()
        if cond_name not in dConditions :
            dConditions[cond_name]=""
    print len(dConditions)

    print "Writting file"
    fileout = open('LINCS_conditions.txt','a')
    for cond in dConditions :
        fileout.write(cond+'\n')