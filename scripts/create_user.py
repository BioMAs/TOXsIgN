#-*- coding: utf-8 -*-
# -----------------------------------------------------------
#
#  Project : TOXsIgN
#  GenOuest / IRSET
#  35000 Rennes
#  France
#
# -----------------------------------------------------------
"""
Created on Sat Jun 18 10:39:10 2016
Author: tdarde <thomas.darde@inria.fr>
Last Update :
"""


########################################################################
#                                                                      #
#    Insert new user in TOXsIgN DB                                     #
#    Don't forget to change the main function arguments                #
#                                                                      #
########################################################################

########################################################################
#                                Functions                             #
# Use this format :                                                    #
#def CreateVersusFile(1,2,3):                                          #
#    """                                                               #
#    Main fonction                                                     #
#    For each projects list all conditions and CAS, create directory   #
#    for condition.                                                    #
#    Create CAS file and treatment.info files                          #
#                                                                      #
#    :param 1: project's path                                          #
#    :param 2: tissue where the studie is performed                    #
#    :param 3: file with a celfile to remove per ligne                 #
#    :type 1: string                                                   #
#    :type 2: string                                                   #
#    :type 3: string                                                   #
#    :return: Condition status                                         #
#    :rtype: string                                                    #
#                                                                      #
#                                                                      #
#    .. todo:: fix error with multi txt files and CAS files            #
#    """                                                               #
#                                                                      #
########################################################################



########################################################################
#                                Import                                #
########################################################################

import argparse
import sys
from hashlib import sha1
from random import randint
import bcrypt
import ConfigParser, os
from hashlib import sha1
from pymongo import MongoClient

########################################################################
#                                Arg parse                             #
########################################################################
parser = argparse.ArgumentParser(description='Initialize database content.')
parser.add_argument('--config')
parser.add_argument('--pwd')
parser.add_argument('--email')
args = parser.parse_args()

if not args.config:
    print "config argument is missing"
    sys.exit(2)

config = ConfigParser.ConfigParser()
config.readfp(open(args.config))

if not args.email:
    print 'email parameter is missing'
    sys.exit(1)

########################################################################
#                                DB connection                         #
########################################################################
print config.get('app:main','db_uri')
mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]

########################################################################
#                                Main                                  #
########################################################################
user_in_db = db['users'].find_one({'id': args.email})
if user_in_db is not None:
    print "User already exists"
    sys.exit(1)

user_password = bcrypt.hashpw(args.pwd, bcrypt.gensalt())
db['users'].insert({'id': args.email,
                    'status': 'approved',
                    'password': user_password,
                    })
