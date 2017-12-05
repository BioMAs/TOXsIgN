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
#    Reformat ontology file get from Fred TCL script                   #
#    Add all the parent name column                                    #
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
import os


########################################################################
#                                Main                                  #
########################################################################
#path="/home/genouest/bioinfo/irset/toxsign/Data/Ontology/"
path="/Users/tdarde/Desktop/"
for files in os.listdir(path):
    #if files != 'chebi.obo.tab' and files != '.DS_Store':
    if files == 'doid.obo.tab':
        print files
        ontofile = open(path+files,'r')
        dName = {}
        for lines in ontofile.readlines():
            ID = lines.split('\t')[0]
            Name = lines.split('\t')[2].rstrip()
            dName[ID] = Name
        ontofile.close
        
        ontofile = open(path+files,'r')
        finalname = files.replace('.obo.tab','.txs').replace('.obo.txt.tab','.txs')
        #finaltabObo = open('Ontology/'+finalname,'a')
        finaltabObo = open(path+finalname,'a')
        for lines in ontofile.readlines():
            ID = lines.split('\t')[0]
            dbase = lines.split('\t')[1]
            Name = lines.split('\t')[2]
            synonyms = lines.split('\t')[3]
            direct_parent = lines.split('\t')[4]
            aparent = lines.split('\t')[5].rstrip()
            all_parent = lines.split('\t')[5].split("|")
            all_parentName=[]
            for i in all_parent:
                if i.rstrip() in dName :
                    pName = dName[i.rstrip()]
                    all_parentName.append(pName)
            
            allparent = "|".join(all_parentName)
            txt = ID+"\t"+dbase+"\t"+Name+"\t"+synonyms+"\t"+direct_parent+"\t"+aparent+"\t"+allparent+"\n"
            finaltabObo.write(txt)