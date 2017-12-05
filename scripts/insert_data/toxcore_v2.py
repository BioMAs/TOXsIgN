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
    Call by setup.py
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
config.readfp(open('../tox_install.ini'))

mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]
onto_path = config.get('setup','onto_path')
data_path = config.get('setup','data_path')
admin_path = config.get('setup','admin_path')
public_path = config.get('setup','public_path')
drugmatrix_path = config.get('setup','drugmatrix_path')
tggate_path = config.get('setup','tggate_path')
tggatehuman_path = config.get('setup','tggatehuman_path')
human_path = config.get('setup','human_path')



def get_Index(type):
    try:
        logger.debug('Get_Index')
        db[type].update({'id': 1}, {'$inc': {'val': 1}})
        repos = db[type].find({'id': 1})
        for i in repos :
            return i['val']
    
    except:
        logger.debug('Get_Index')
        logger.error(sys.exc_info()[1])


def get_tag(index,val) :
    try:
        logger.debug('get_tag')
        result=[]
        repos = []
        repo = db[index].find({'id': val})
        for val in repo :
            repos = val
        result.append(repos['id'])
        result.append(repos['name'])
        for i in repos['synonyms'] :
            result.append(i)
        for j in repos['direct_parent'] :
            result.append(j)
        for k in repos['all_parent'] :
            result.append(k)
        for z in repos['all_name'] :
            result.append(z)
        return result
    
    except:
        logger.debug('get_tag')
        logger.error(sys.exc_info()[1])

def dicoChemical():
    try :
        logger.debug('dicoChemical')
        chebiTab = open(data_path+'chebi.obo.tab','r')
        dChemical = {}
        for lines in chebiTab.readlines():
            val = lines.split('\t')
            ID = val[0]
            name = val[2]
            syno = val[3].split('|')
            for i in syno :
                dChemical[i] = ID
            dChemical[name] = ID
        return dChemical
    except:
        logger.debug('dicoChemical')
        logger.error(sys.exc_info()[1])

def NewcondDico():
    fileCond = open(data_path+'/condInfo_Human_GSE.txt','r')
    dico_cond={}
    for lines in fileCond.readlines():
        val = lines.split('\t')
        cond_name = val[0]
        if cond_name not in dico_cond :
            dico_cond[cond_name] = val
    return dico_cond

def getFileCas(fileCond):
    try:
        logger.debug('getFileCas')
        casTab = open(data_path+'ChemPSy_MESH.tsv','r')
        dChemical = {}
        for lines in casTab.readlines():
            val = lines.split('\t')
            fileName = val[0]
            CAS = val[4].split('|')[0]
            dChemical[fileName] = CAS
        return dChemical[fileCond]
    except:
        logger.debug('getFileCas')
        logger.error(sys.exc_info()[1])


def getCAS():
    try:
        logger.debug('getCas')
        chebiTab = open(onto_path+'chemical.tab','r')
        dCAS = {}
        for lines in chebiTab.readlines():
            val = lines.split('\t')
            ID = val[0]
            name = val[2]
            CAS = name.split('CAS:')[1]
            dCAS[CAS] = [name,ID]
        return dCAS
    except:
        logger.debug('getCas')
        logger.error(sys.exc_info()[1])


def dicoRoute(project):
    try:
        logger.debug('dicoRoute')
        dRoute ={}
        routeFile = open(project+'.txt','r')   
        for lines in routeFile.readlines():
            val = lines.split('\t')
            chem = val[5].lower()
            route = val[9]
            dRoute[chem] = route
        
        return dRoute
    except:
        logger.debug('dicoRoute')
        logger.error(sys.exc_info()[1])


def NewdicoRoute(project):
    dRoute ={}
    routeFile = open(human_path+'/'+project+'.txt','r')
    lines = routeFile.readlines()
    for i in range(1,len(lines)):
        val = lines[i].split('\t')
        chem = val[8].lower()
        route = val[13]
        dRoute[chem] = route

    return dRoute

def dicoCAS():
    try:
        logger.debug('dicoCas')
        casTab = open(data_path+'ChemPSy_MESH.tsv','r')
        dChemical = {}
        for lines in casTab.readlines():
            val = lines.split('\t')
            fileName = val[0]
            name = val[1]
            dChemical[fileName] = name
        return dChemical
    except:
        logger.debug('dicoCas')
        logger.error(sys.exc_info()[1])


def dicoSample():
    try:
        logger.debug('dicoSample')
        files = open(data_path+'ChemPSySampleNumber.txt','r')
        dSample = {}
        for lines in files.readlines():
            val = lines.split('\t')
            name = val[0]
            nb_sample = val[1]
            nb_control = val[2]
            dSample[name] = [nb_sample,nb_control]
        return dSample
    except:
        logger.debug('dicoSample')
        logger.error(sys.exc_info()[1])
        
def dicoSampleHuman():
    try:
        logger.debug('dicoSample')
        files = open(data_path+'ChemPSySampleNumberHuman.txt','r')
        dSample = {}
        for lines in files.readlines():
            val = lines.split('\t')
            name = val[0]
            nb_sample = val[1]
            nb_control = val[2]
            dSample[name] = [nb_sample,nb_control]
        return dSample
    except:
        logger.debug('dicoSample')
        logger.error(sys.exc_info()[1])

def condDico():
    fileCond = open(data_path+'condInfo.txt','r')
    dico_cond={}
    for lines in fileCond.readlines():
        val = lines.split('\t')
        cond_name = val[0]
        if cond_name not in dico_cond :
            dico_cond[cond_name] = val
    return dico_cond

def getFileCasHuman(fileCond):
    casTab = open(data_path+'ChemPSy_MESH_human.tsv','r')
    dChemical = {}
    for lines in casTab.readlines():
        val = lines.split('\t')
        fileName = val[0]
        CAS = val[4].split('|')[0]
        dChemical[fileName] = CAS
    return dChemical[fileCond]


def toxOrg(pro):
    try:
        logger.debug('toxOrg')
        toxF = open(data_path+'ChemPSy_MESH.tsv','r')
        dChemical = {}
        for lines in toxF.readlines():
            if pro in lines :
                name = lines.split('\t')[0]
                study = lines.split('\t')[0].split('+')[1]
                cond = lines.split('\t')[0].split('+')[4]+"+"+lines.split('\t')[0].split('+')[5]
                project = lines.split('\t')[1]
                if project not in dChemical :
                    dChemical[project]={}
                if study not in dChemical[project] :
                    dChemical[project][study] = {}
                if cond not in dChemical[project][study] :
                    dChemical[project][study][cond] = name
        return dChemical
    except:
        logger.debug('toxOrg')
        logger.error(sys.exc_info()[1])

def human_toxOrg(pro):
    try:
        logger.debug('toxOrg Human')
        toxF = open(data_path+'ChemPSy_MESH_human.tsv','r')
        dChemical = {}
        for lines in toxF.readlines():
            if pro in lines :
                name = lines.split('\t')[0]
                study = lines.split('\t')[0].split('+')[1]
                cond = lines.split('\t')[0].split('+')[4]+"+"+lines.split('\t')[0].split('+')[5]
                project = lines.split('\t')[1]
                if project not in dChemical :
                    dChemical[project]={}
                if study not in dChemical[project] :
                    dChemical[project][study] = {}
                if cond not in dChemical[project][study] :
                    dChemical[project][study][cond] = name
        return dChemical
    except:
        logger.debug('toxOrg Human')
        logger.error(sys.exc_info()[1])


"""
    ------  Create demo user  ------
    Create a demonstration user for TOXsIgN collections
    
"""
def CreateDemoUser():
    try :
        logger.debug('CreateDemoUser')
        user_id = "demo@toxsign.genouest.org"
        status = "approved"
        password = "XaOP13atGK@@13"
        first_name = "Demo 1"
        last_name = ""
        institute = "INSERM"
        laboratory = "IRSET"
        address = "9 avenue du professeur Léon Bernard"
        referent = ""
        user_password = bcrypt.hashpw(password, bcrypt.gensalt())
        db['users'].insert({'id': user_id,
                        'status': status,
                        'password': user_password,
                        'first_name': first_name,
                        'last_name': last_name,
                        'institute': institute,
                        'laboratory': laboratory,
                        'address': address,
                        'referent': referent,
                        'tool_history': [],
                        'selectedID':[]
                    })
    except:
        logger.debug('CreateDemoUser')
        logger.error(sys.exc_info()[1])
    
"""
    ------  Collections creation  ------
    Create TOXsIgN collections
    Use parsed and formated file for ontologies
    Need genes.info, homologenes.txt and TOXsIgN_geneDB files
"""
def createCounters():
    try :
        logger.debug('CreateCollection - Create projects counters')
        db['project'].insert({'id': 1,
                             'val': 0,
                             })
        db['study'].insert({'id': 1,
                             'val': 0,
                             })
        db['assay'].insert({'id': 1,
                             'val': 0,
                             })
        db['factor'].insert({'id': 1,
                             'val': 0,
                             })
        db['signature'].insert({'id': 1,
                             'val': 0,
                             })
        db['Jobs'].insert({'id': 1,
                            'val': 0,
                            })

    except:
        logger.debug('CreateCollection - Create projects counters')
        logger.error(sys.exc_info()[1])


def chemicalDB():
    try:
        logger.debug('CreateCollection - insert ontologies')
        for files in os.listdir(onto_path):
            if files == 'chemical.tab':
                print "INSERT: "+files
                fileIn = open(onto_path+files,'r')
                for lines in fileIn.readlines():
                    ids = lines.split('\t')[0]
                    dbs = files
                    if dbs == "go.obo.tab" :
                        dbs = lines.split('\t')[1]
                    name = lines.split('\t')[2]
                    synonyms = lines.split('\t')[3].split("|")
                    direct_parent = lines.split('\t')[4].split("|")
                    all_parent = lines.split('\t')[5].split("|")
                    all_parent_name = lines.split('\t')[6].split("|")
                    #print dbs,ids
                    db[dbs].insert({'id': ids,
                                 'name': name,
                                 'synonyms': synonyms,
                                 'direct_parent': direct_parent,
                                 'all_parent': all_parent,
                                 'all_name': all_parent_name,
                                 })
    except:
        logger.debug('chemicalDB - insert ontologies')
        logger.error(sys.exc_info()[1])
def createCollections():

    
    try:
        logger.debug('CreateCollection - insert ontologies')
        for files in os.listdir(onto_path):
            if files != '.DS_Store':
                print "INSERT: "+files
                fileIn = open(onto_path+files,'r')
                for lines in fileIn.readlines():
                    ids = lines.split('\t')[0]
                    dbs = files
                    if dbs == "go.obo.tab" :
                        dbs = lines.split('\t')[1]
                    name = lines.split('\t')[2]
                    synonyms = lines.split('\t')[3].replace("EXACT",'').split("|")
                    direct_parent = lines.split('\t')[4].split("|")
                    all_parent = lines.split('\t')[5].split("|")
                    all_parent_name = lines.split('\t')[6].split("|")
                    #print dbs,ids
                    db[dbs].insert({'id': ids,
                                 'name': name,
                                 'synonyms': synonyms,
                                 'direct_parent': direct_parent,
                                 'all_parent': all_parent,
                                 'all_name': all_parent_name,
                                 })
    except:
        logger.debug('CreateCollection - insert ontologies')
        logger.error(sys.exc_info()[1])
    
    try:
        logger.debug('CreateCollection - create geneInfo collection')
        #Create geneInfo db from geneInfo file
        geneFile = open(data_path+'gene_info_parse','r')
        for geneLine in geneFile.readlines():
            if geneLine[0] != '#':
                tax_id = geneLine.split('\t')[0]
                GeneID = geneLine.split('\t')[1]
                Symbol = geneLine.split('\t')[2] 
                Synonyms = geneLine.split('\t')[4] 
                description = geneLine.split('\t')[8]
                db['geneInfo'].insert({'GeneID': GeneID,
                                  'tax_id' : tax_id,
                                  'Symbol': Symbol,
                                  'Synonyms': Synonyms,
                                  'description': description,
                                  })
        geneFile.close()
    except:
        logger.debug('CreateCollection - create geneInfo collection')
        logger.error(sys.exc_info()[1])
    
    try:
        logger.debug('CreateCollection - create homoloGene collection')
        #Insert homologene ID from homologene.data.txt file
        homologeneFile = open(data_path+'homologene.data.txt','r')
        for homoline in homologeneFile.readlines():
            HID = homoline.split('\t')[0]
            Taxonomy_ID = homoline.split('\t')[1]
            Gene_ID = homoline.split('\t')[2]
            Gene_Symbol = homoline.split('\t')[3]
            Protein_gi = homoline.split('\t')[4]
            Protein_accession = homoline.split('\t')[5]
            db['homoloGene'].insert({'HID': HID,
                                   'Taxonomy_ID' : Taxonomy_ID,
                                   'Gene_ID': Gene_ID,
                                   'Gene_Symbol': Gene_Symbol,
                                   'Protein_gi': Protein_gi,
                                   'Protein_accession': Protein_accession,
                                   })
        homologeneFile.close()
    except:
        logger.debug('CreateCollection - create homoloGene collection')
        logger.error(sys.exc_info()[1])
    
    
    try :
        logger.debug('CreateCollection - create TOXsIgN_geneDB collection')
        #Insert Allbank ID from TOXsIgN_geneDB file
        geneFile = open(data_path+'TOXsIgN_geneDB','r')
        for geneLine in geneFile.readlines():
            if geneLine[0] != '#':
                tax_id = geneLine.split('\t')[0]
                GeneID = geneLine.split('\t')[1]
                Symbol = geneLine.split('\t')[2] 
                Synonyms = geneLine.split('\t')[4] 
                description = geneLine.split('\t')[8]
                HID = geneLine.split('\t')[-1]
                db['genes'].insert({'GeneID': GeneID,
                                 'tax_id' : tax_id,
                                 'Symbol': Symbol,
                                 'Synonyms': Synonyms,
                                 'description': description,
                                 'HID':HID,
                                 })
        geneFile.close()
    except:
        logger.debug('CreateCollection - create TOXsIgN_geneDB collection')
        logger.error(sys.exc_info()[1])
    
    
    
    """
    ------  Insertion part  ------
    There is 3 kind of insertion : 
        insertDM : Insert all signatures from DrugMatrix project
        insertTG : Insert TGGates signatures performed on the rat
        insertHumanTG : Insert TGGates signatures performed on the human
    TO DO : (modifie) insertHuman information from GEO dowload and processing signatures
    For database insertion issue, projects are organized as describe : chemical tested > organes where the chemical is tested
"""

def insertDM():
    """
        Insert signatures extrated from ChemPSY processing
        To insert informations please make sur that the following repository is correctlly filled :
            - all_genes_converted files
            - Conditions repository with all individuals conditions
            - Description.txt file
            - projectName.txt file 
            - Studies directory
        This function also required :
            - Individual sample file (Data/files/ChemPSySampleNumber.txt)
            - ChemPSy_MESH.tsv file (Data/files/ChemPSy_MESH.tsv)
    """
    logger.debug('InsertDM - Load dictionnaries')
    projectPath = drugmatrix_path
    projectName = 'DrugMatrix'
    dChemical = dicoCAS()
    dDataset = {}
    dRoute = dicoRoute(drugmatrix_path+'/'+projectName)
    dCAS = dicoCAS()
    dSample=dicoSample()
    dName = {}
    
    nb_dataset = 0
    nb_study = 0
    nb_cond = 0
    
    orga = toxOrg('GSE578')



    #DEFINITION DES CONDITIONS PAR CHEMICAL
    logger.debug('InsertDM - Create dico condition')
    for files in os.listdir(projectPath+'Conditions'):
        name = files.replace('_down.txt','').replace('_up.txt','').replace('_noeffects.txt','')
        if 'GSE578' in name :
            if name not in dDataset :
                dDataset[name] =[]



    logger.debug('InsertDM - Insert project')
    for project in orga :
        logger.info(project)
        #print project
        project_id = 0
        study_id = 0
        assay_id = 0
        factor_id = 0
        signature_id = 0
        projects = {}
        studies = {}
        assays = {}
        factors = {}
        signatures = {}
        asso_id = {}
        reverse_asso = {}
        
        
        
        project_id += 1
        
        Dataset_authors = 'Scott S. Auerbach'
        Dataset_email = 'auerbachs@niehs.nih.gov'
        Dataset_conditions = []
        Dataset_contributors=['TOXsIgN Team']
        Dataset_pubmed = ['16005536','25058030']
        Dataset_extlink = "https://www.niehs.nih.gov/research/atniehs/labs/bmsb/toxico/index.cfm,https://ntp.niehs.nih.gov/drugmatrix/index.html,http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE57800,http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE57805,http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE57811,http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE57815,http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE57816"
        Dataset_description = "DrugMatrix is the scientific communities' largest molecular toxicology reference database and informatics system. DrugMatrix is populated with the comprehensive results of thousands of highly controlled and standardized toxicological experiments in which rats or primary rat hepatocytes were systematically treated with therapeutic, industrial, and environmental chemicals at both non-toxic and toxic doses."
        Dataset_owner = 'auerbachs@niehs.nih.gov'
        Dataset_status = "public"
        Dataset_ID = 'TSP' + str(get_Index('project'))
        Dataset_title = projectName+" - Toxicogenomic signatures after exposure to "+project+" in the rat"

        # DATASET CREATION
        dt = datetime.datetime.utcnow()
        ztime = mktime(dt.timetuple())
        dico={
                'id' : Dataset_ID,
                'title' : Dataset_title,
                'description' : Dataset_description,
                'pubmed' : ','.join(Dataset_pubmed),
                'contributor' : ','.join(Dataset_contributors),
                'assays' : "",
                'studies' : "",
                'factors' : "",
                'cross_link' : Dataset_extlink,
                'signatures' :"",
                'last_update' : str(ztime),
                'submission_date' : str(ztime),
                'status' : 'public' ,
                'owner' : Dataset_owner,
                'author' : Dataset_authors ,
                'tags' : "",
                'edges' : "",
                'info' : "",
                'warnings' : "",
                'critical' : "",
                'excel_id' : 'PR'+str(project_id)
            }
        
        #Add to dico
        print "########################    PROJECT    ########################"
        asso_id['PR'+str(project_id)] = Dataset_ID
        print asso_id['PR'+str(project_id)]
        reverse_asso[asso_id['PR'+str(project_id)]] = 'PR'+str(project_id)
        projects['PR'+str(project_id)] = dico
        print "###############################################################"
        
        
        nb_dataset = nb_dataset + 1
        
        
        #Create project excel
        title_line = 5 
        project_path = os.path.join(public_path,Dataset_ID)
        os.makedirs(project_path)



        workbook = xlsxwriter.Workbook(project_path+'/TOXsIgN_'+Dataset_ID+'.xlsx')
        project_worksheet = workbook.add_worksheet('Projects')
        study_worksheet = workbook.add_worksheet('Studies')
        asssay_worksheet = workbook.add_worksheet('Assays')
        factor_worksheet = workbook.add_worksheet('Factors')
        signature_worksheet = workbook.add_worksheet('Signatures')
        project_worksheet.write('A1', '# TOXsIgN - Excel template version 0.3')
        project_worksheet.write('C1', '# Fill the project description')
        project_worksheet.write('C2', '# Each project is defined by one unique title (one by line)')
        project_worksheet.write('C3', '# A project is the global description of your studies')
        project_worksheet.write('A5', 'Project Id')
        project_worksheet.write('B5', 'Title')
        project_worksheet.write('C5', 'Description')
        project_worksheet.write('D5', 'PubMed Id(s) (comma separated)')
        project_worksheet.write('E5', 'Contributors (comma separated)')
        project_worksheet.write('F5', 'Cross link(s) (comma separated)')
        project_worksheet.write('A'+str(title_line + project_id), 'PR'+str(project_id))
        project_worksheet.write('B'+str(title_line + project_id), Dataset_title)
        project_worksheet.write('C'+str(title_line + project_id), Dataset_description)
        project_worksheet.write('D'+str(title_line + project_id), ','.join(Dataset_pubmed))
        project_worksheet.write('E'+str(title_line + project_id), ','.join(Dataset_contributors))
        project_worksheet.write('F'+str(title_line + project_id), Dataset_extlink)
        
        organeList = ['LIVER','KIDNEY','HEART','THIGH-MUSCLE']
        for studorg in organeList  :
            if studorg in orga[project]:
                study_id += 1
                print studorg

                study = studorg
                #print study


                tissue_name = ''
                tissue_ID = ''
                study_description = ''
                if study == 'LIVER' :
                    tissue_name = 'Liver'
                    tissue_ID = 'FMA:7197'
                    study_description = "Complete Drug Matrix dataset for rat liver."
                if study == 'KIDNEY' :
                    tissue_name = 'Kidney'
                    tissue_ID = 'FMA:7203'
                    study_description = "Complete Drug Matrix dataset for rat kidney."
                if study == 'HEART' :
                    tissue_name = 'Heart'
                    tissue_ID = 'FMA:7088'
                    study_description = "Complete Drug Matrix dataset for rat heart."
                if study == 'THIGH-MUSCLE' :
                    tissue_name = 'Skeletal muscle tissue'
                    tissue_ID = 'FMA:14069'
                    study_description = "Complete Drug Matrix dataset for rat thigh muscle."
                


                print "########################    Study    ########################"
                study_projects = 'PR'+str(project_id)
                #Excel id -> databas id
                asso_id['St'+str(study_id)] = 'TSE' + str(get_Index('study'))
                print asso_id['St'+str(study_id)]
                reverse_asso[asso_id['St'+str(study_id)]] = study_id
    
                #Add studies id to associated project
                p_stud = projects[study_projects]['studies'].split()
                p_stud.append(asso_id['St'+str(study_id)])
                projects[study_projects]['studies'] = ','.join(p_stud)
                print "add to " + study_projects + "----> " + str(p_stud)
                print "###############################################################"
    
                dico={
                    'id' : asso_id['St'+str(study_id)],
                    'owner' : Dataset_owner,
                    'projects' : asso_id['PR'+str(project_id)],
                    'assays' : "",
                    'factors' : "",
                    'signatures' : "",
                    'title' : projectName+" - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the rat",
                    'description' : study_description,
                    'experimental_design' : "Approximately 600 different compounds were profiled in up to 7 different rat tissues by obtaining tissue samples from test compound-treated and vehicle control-treated rats in biological triplicates for gene expression analysis after 0.25, 1, 3, and 5 days of exposure with daily dosing. In a few studies (1.8%), 7 days of exposure was substituted for 5 days of exposure. Samples were hybridized to whole genome RG230_2.0 GeneChip arrays (Affymetrix, CA).  DrugMatrix is a comprehensive rat toxicogenomics database and analysis tool developed to facilitate the integration of toxicogenomics into hazard assessment. Using the whole genome and a diverse set of compounds allows a comprehensive view of most pharmacological and toxicological questions and is applicable to other situations such as disease and development. Male Sprague–Dawley (Crl:CD (SD)|GS BR) rats(aged 6–8 weeks) were purchased from Charles River Laboratories (Wilmington, MA). They were housed in plastic cages for 1 week for acclimation to the laboratory environment of a ventilated room (temperature, 22 +- 3 C; humidity 30–70%; 12-h light:12-h dark cycle per day, 6:00 a.m.- 6:00 p.m.) until use. Certified Rodent Diet #5002 (PMI Feeds Inc.) and chlorinated tap water was available ad libitum.",
                    'results' : "",
                    'study_type' : 'Interventional',
                    'last_update' : str(ztime),
                    'inclusion_period': "",
                    'inclusion': "",
                    'exclusion': "",
                    'status' : 'public',
                    'followup': "",
                    'population_size' : "",
                    'pubmed' : "",
                    'tags' : "",
                    'info' : "",
                    'warnings' : "",
                    'critical' : "",
                    'excel_id' : 'St'+str(study_id)
                }      
                
                studies['St'+str(study_id)]=dico
                
                #Create study excel
                title_line = 6 
                
                format = workbook.add_format()
                format.set_pattern(1)  # This is optional when using a solid fill.
                format.set_bg_color('green')

                study_worksheet.write('C1', '# Fill the study description')
                study_worksheet.write('C2', '# Each study is defined by one unique title (one by line) need to be associated with only one project')
                study_worksheet.write('C3', '# A study is the detail description of your experimentations')
                study_worksheet.write('C4', 'Only for observational studies',format)
                
                study_worksheet.write('A6', 'Study Id')
                study_worksheet.write('B6', 'Associated project')
                study_worksheet.write('C6', 'Study Title')
                study_worksheet.write('D6', 'Description')
                study_worksheet.write('E6', 'Design')
                study_worksheet.write('F6', 'Results')
                study_worksheet.write('G6', 'Study type ')
                study_worksheet.write('H6', 'Inclusion period')
                study_worksheet.write('I6', 'Inclusion criteria')
                study_worksheet.write('J6', 'Exclusion criteria')
                study_worksheet.write('K6', 'Follow up')
                study_worksheet.write('L6', 'Pubmed Id(s) (comma separated)')
                study_worksheet.write('M6', 'Interventional')
                
                study_worksheet.write('A'+str(title_line + study_id), 'St'+str(study_id))
                study_worksheet.write('B'+str(title_line + study_id), 'PR'+str(project_id))
                study_worksheet.write('C'+str(title_line + study_id), projectName+" - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the rat")
                study_worksheet.write('D'+str(title_line + study_id), study_description)
                study_worksheet.write('E'+str(title_line + study_id), str("Approximately 600 different compounds were profiled in up to 7 different rat tissues by obtaining tissue samples from test compound-treated and vehicle control-treated rats in biological triplicates for gene expression analysis after 0.25, 1, 3, and 5 days of exposure with daily dosing. In a few studies (1.8%), 7 days of exposure was substituted for 5 days of exposure. Samples were hybridized to whole genome RG230_2.0 GeneChip arrays (Affymetrix, CA).  DrugMatrix is a comprehensive rat toxicogenomics database and analysis tool developed to facilitate the integration of toxicogenomics into hazard assessment. Using the whole genome and a diverse set of compounds allows a comprehensive view of most pharmacological and toxicological questions and is applicable to other situations such as disease and development. Male Sprague–Dawley (Crl:CD (SD)/GS BR) rats(aged 6–8 weeks) were purchased from Charles River Laboratories (Wilmington, MA). They were housed in plastic cages for 1 week for acclimation to the laboratory environment of a ventilated room (temperature, 22° +/- 3°C; humidity 30–70%; 12h light: 12h dark cycle per day, 6:00 a.m.- 6:00 p.m.) until use. Certified Rodent Diet #5002 (PMI Feeds Inc.) and chlorinated tap water was available ad libitum.").decode('utf-8') )
                study_worksheet.write('F'+str(title_line + study_id), "")
                study_worksheet.write('G'+str(title_line + study_id), "")
                
                
                for cond in orga[project][studorg] :
                    assay_id += 1
                    dose = cond.split('+')[0]
                    print cond
                    temps = cond.split('+')[1]
                    print temps
                     #CREATION INFORMATION CONDITION

                     #RECUPERATION NOM | CAS | ROUTE DU CHEMICAL
                    condName = orga[project][studorg][cond]
                    prezfile = 1
                    if condName in dDataset :
                        upFile = open(projectPath+'Conditions/'+condName+'_up.txt','r')
                        downFile = open(projectPath+'Conditions/'+condName+'_down.txt','r')
                    else :
                        prezfile = 0

                    CAS = getFileCas(condName)
                    dCas = getCAS()
                    if CAS.rstrip() not in dCas :
                        chemName = files.split('+')[2]+' CAS:NA'
                        chemID = ""
                    else :
                        chemName = dCas[CAS.rstrip()][0]
                        chemID = dCas[CAS.rstrip()][1]
                    chemRoute = ""
                    if condName in dCAS :
                        if dCAS[condName] in dRoute :
                            chemRoute = dRoute[dCAS[condName]]
                        else :
                            chemRoute = "other"
                    
    
                   
                    if chemID != "" :
                         chemtag = get_tag('chemical.tab',chemID)
                    else : 
                        chemtag =chemName
                  
                    doses = dose.split('_')[0]
                    dose_unit = dose.split('_')[1].replace('mgkg','mg/kg')
                    exposure = temps.split('_')[0]
                    exposure_unit = temps.split('_')[1]
                    timeexpo = 0
                    # CHANGE TIME UNIT
                    if exposure_unit == 'd' :
                        exposure_unit = "days"
                        timeexpo = float(exposure) * 1440
                    if exposure_unit == 'hr' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'h' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'min' :
                        exposure_unit = "minutes"
                        timeexpo = float(exposure) * 1
                        
                    #Excel id -> databas id
                    asso_id['As'+str(assay_id)] = 'TSA'+str(get_Index('assay'))
                    reverse_asso[asso_id['As'+str(assay_id)]] = 'As'+str(assay_id)
        
                    #Add assay id to associated study
                    s_assay = studies['St'+str(study_id)]['assays'].split()
                    s_assay.append(asso_id['As'+str(assay_id)])
                    studies['St'+str(study_id)]['assays'] = ','.join(s_assay)
        
                    #Add assay to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
                    print project_asso
        
                    p_assay = projects['PR'+str(project_id)]['assays'].split()
                    p_assay.append(asso_id['As'+str(assay_id)])
                    projects['PR'+str(project_id)]['assays'] = ','.join(p_assay)
        
                    #After reading line add all info in dico project
                    tag = get_tag('species.tab','NCBITaxon:10116')
                    tissue_tag = get_tag('tissue.tab',tissue_ID)
                    tag.extend(tissue_tag)
                    
                    dico={
                        'id' : asso_id['As'+str(assay_id)] ,
                        'studies' : asso_id['St'+str(study_id)],
                        'factors' : "",
                        'signatures' : "",
                        'projects' : studies['St'+str(study_id)]['projects'],
                        'title' : projectName+" - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the rat",
                        'organism' : 'Rattus norvegicus',
                        'experimental_type' : 'in vivo',
                        'developmental_stage' : 'Adulthood',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'tissue' : tissue_name,
                        'cell' : "",
                        'status' : 'public',
                        'last_update' : str(ztime),
                        'cell_line' : "",
                        'additional_information' : "",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'As'+str(assay_id),
                        'pop_age' : "",
                        'location': "",
                        'reference' : "",
                        'matrice' : ""
                    }
                    assays['As'+str(assay_id)] = dico
                    
                    #Create study excel
                    title_line = 12 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    asssay_worksheet.write('A12', 'Assay Id')
                    asssay_worksheet.write('B12', 'Associated study')
                    asssay_worksheet.write('C12', 'Title')
                    asssay_worksheet.write('D12', 'Organism')
                    asssay_worksheet.write('E12', 'Developmental stage')
                    asssay_worksheet.write('F12', 'Generation')
                    asssay_worksheet.write('G12', 'Sex')
                    asssay_worksheet.write('H12', 'Tissue')
                    asssay_worksheet.write('I12', 'Cell')
                    asssay_worksheet.write('J12', 'Cell Line')
                    asssay_worksheet.write('K12', 'Experimental type')
                    asssay_worksheet.write('L12', 'Additional information')
                    asssay_worksheet.write('M12', 'Population age')
                    asssay_worksheet.write('N12', 'Geographical location')
                    asssay_worksheet.write('O12', 'Controle / Reference')
                    asssay_worksheet.write('P12', 'Biological matrice')
                    
                    asssay_worksheet.write('A'+str(title_line + assay_id), 'As'+str(assay_id))
                    asssay_worksheet.write('B'+str(title_line + assay_id), 'St'+str(study_id))
                    asssay_worksheet.write('C'+str(title_line + assay_id), projectName+" - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the rat")
                    asssay_worksheet.write('D'+str(title_line + assay_id), 'NCBITaxon:10116')
                    asssay_worksheet.write('E'+str(title_line + assay_id), 'Adulthood')
                    asssay_worksheet.write('F'+str(title_line + assay_id), "f0")
                    asssay_worksheet.write('G'+str(title_line + assay_id), "Male")
                    asssay_worksheet.write('H'+str(title_line + assay_id), tissue_ID)
                    asssay_worksheet.write('K'+str(title_line + assay_id), 'in vivo')
                    
                    factor_id += 1
                                        
                    
                    #Excel id -> databas id
                    asso_id['Fc'+str(factor_id)] = 'TSF'+str(get_Index('factor'))
                    reverse_asso[asso_id['Fc'+str(factor_id)]] = 'Fc'+str(factor_id)
        
                    #Add factor id to associated assay
                    a_factor = assays['As'+str(assay_id)]['factors'].split()
                    a_factor.append(asso_id['Fc'+str(factor_id)])
                    assays['As'+str(assay_id)]['factors'] = ','.join(a_factor)
        
                    #Add factor to the associated study
                    study_asso = reverse_asso[assays['As'+str(assay_id)]['studies']]
        
                    s_factor = studies['St'+str(study_id)]['factors'].split()
                    s_factor.append(asso_id['Fc'+str(factor_id)])
                    studies['St'+str(study_id)]['factors'] = ','.join(s_factor)
        
                    #Add factor to the associated project
                    project_asso = assays['As'+str(assay_id)]['projects']
        
                    p_factor = projects['PR'+str(project_id)]['factors'].split()
                    p_factor.append(asso_id['Fc'+str(factor_id)])
                    projects['PR'+str(project_id)]['factors'] = ','.join(p_factor)

                    tag.extend(chemtag)
                    myset = list(set(tag))
                    tag = myset
        

        
                    #After reading line add all info in dico project
                    dico={
                        'id' : asso_id['Fc'+str(factor_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'studies' : assays['As'+str(assay_id)]['studies'],
                        'project' : assays['As'+str(assay_id)]['projects'],
                        'type' : "Chemical",
                        'chemical' : chemName,
                        'physical' : "",
                        'biological' : "",
                        'route' : chemRoute,
                        'last_update' : str(ztime),
                        'status' : 'public',
                        'vehicle' : 'NA',
                        'dose' : str(doses) +" "+ dose_unit,
                        'exposure_duration' : str(exposure) +" "+ exposure_unit,
                        'exposure_frequencies' : "",
                        'additional_information' : "For the in vivo studies, the highest dose was selected to match the level demonstrated to induce the minimum toxic effect over the course of a 4-week toxicity study. In principle, the ratio of the concentrations for the low, middle and high dose levels was set as 1:3:10. ",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Fc'+str(factor_id)
                    }
                    factors['Fc'+str(factor_id)] = dico


                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    factor_worksheet.write('A6', 'Factor Id')
                    factor_worksheet.write('B6', 'Associated assay')
                    factor_worksheet.write('C6', 'Exposition factor')
                    factor_worksheet.write('D6', 'Chemical name')
                    factor_worksheet.write('E6', 'Physical')
                    factor_worksheet.write('F6', 'Biological')
                    factor_worksheet.write('G6', 'Route')
                    factor_worksheet.write('H6', 'Vehicle')
                    factor_worksheet.write('I6', 'Dose')
                    factor_worksheet.write('J6', 'Dose unit')
                    factor_worksheet.write('K6', 'Exposure duration')
                    factor_worksheet.write('L6', 'Exposure duration unit')
                    factor_worksheet.write('M6', 'Exposure frequecies')
                    factor_worksheet.write('N6', 'Additional information')

                    
                    factor_worksheet.write('A'+str(title_line + factor_id), 'Fc'+str(factor_id))
                    factor_worksheet.write('B'+str(title_line + factor_id), 'As'+str(assay_id))
                    factor_worksheet.write('C'+str(title_line + factor_id), "Chemical")
                    factor_worksheet.write('D'+str(title_line + factor_id), chemName)
                    factor_worksheet.write('E'+str(title_line + factor_id), "")
                    factor_worksheet.write('F'+str(title_line + factor_id), "")
                    factor_worksheet.write('G'+str(title_line + factor_id), chemRoute)
                    factor_worksheet.write('H'+str(title_line + factor_id), 'NA')
                    factor_worksheet.write('I'+str(title_line + factor_id), str(doses))
                    factor_worksheet.write('J'+str(title_line + factor_id), dose_unit)
                    factor_worksheet.write('K'+str(title_line + factor_id), str(exposure))
                    factor_worksheet.write('L'+str(title_line + factor_id), exposure_unit)
                    factor_worksheet.write('M'+str(title_line + factor_id), '')
                    factor_worksheet.write('N'+str(title_line + factor_id), '')
                    
                    
                    signature_id += 1
                    
                    #Excel id -> databas id
                    asso_id['Si'+str(signature_id)] = 'TSS'+str(get_Index('signature'))
                    reverse_asso[asso_id['Si'+str(signature_id)]] = 'Si'+str(signature_id)
        
                    #Add signature id to associated assay
                    a_signature = assays['As'+str(assay_id)]['signatures'].split()
        
                    a_signature.append(asso_id['Si'+str(signature_id)])
                    assays['As'+str(assay_id)]['signatures'] = ','.join(a_signature)
        
                    #Add factor to the associated study
        
                    s_signature = studies['St'+str(study_id)]['signatures'].split()
                    s_signature.append(asso_id['Si'+str(signature_id)])
                    studies['St'+str(study_id)]['signatures'] = ','.join(s_signature)
        
                    #Add factor to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
        
                    p_signature = projects['PR'+str(project_id)]['signatures'].split()
                    p_signature.append(asso_id['Si'+str(signature_id)])
                    projects['PR'+str(project_id)]['signatures'] = ','.join(p_signature)
        
                    #get factors
                    tag.extend(get_tag('experiment.tab','OBI:0400147'))
                    myset = list(set(tag))
                    tag = myset
                    
                    
                   
                   
                    dirCond = public_path+Dataset_ID+"/"+asso_id['Si'+str(signature_id)]
                    geneup = []
                    genedown = []
                    interofile =""
                    file_up = ""
                    file_down = ""
                
                    os.makedirs(dirCond)
                    if prezfile == 1:
                        upfile = condName+'_up.txt'
                        lId = []
                        for idline in upFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            geneup.append(idline.replace('\n',''))
                        lId = list(set(lId))
                        upFile.close()
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_up.txt')):
                            os.remove(os.path.join(dirCond,condName+'_up.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_up.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                
                        check_files.close()
                        
                        
                        
                        downfile = condName+'_down.txt'
                        lId = []
                        for idline in downFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            genedown.append(idline.replace('\n',''))
                        downFile.close()
                        lId = list(set(lId))
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_down.txt')):
                            os.remove(os.path.join(dirCond,condName+'_down.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_down.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                  
                        check_files.close() 
               
            
                        
                        
                        
                    if os.path.isfile(os.path.join(dirCond,'genomic_interrogated_genes.txt')):
                        os.remove(os.path.join(dirCond,'genomic_interrogated_genes.txt'))
                    interofile = 'genomic_interrogated_genes.txt'
                    cmd3 = 'cp %s %s' % (projectPath+'all_genes_converted.txt',dirCond+'/genomic_interrogated_genes.txt')
                    os.system(cmd3)
                    
                    
                    
                    upload_path = admin_path
                    all_name = asso_id['Si'+str(signature_id)]+'.sign'
                    adm_path_signame = os.path.join(upload_path,'signatures_data',all_name)
                    #admin
                    if not os.path.exists(os.path.join(upload_path,'signatures_data')):
                        os.makedirs(os.path.join(upload_path,'signatures_data'))
                    if os.path.isfile(adm_path_signame):
                        os.remove(adm_path_signame)
                
                    check_files = open(adm_path_signame,'a')
                    lfiles = {'genomic_upward.txt':'1','genomic_downward.txt':'-1','genomic_interrogated_genes.txt':'0'}
                    val_geno = 0
                    for filesUsr in os.listdir(dirCond) :
                        if filesUsr in lfiles:
                            fileAdmin = open(dirCond +'/'+filesUsr,'r')
                            print dirCond +'/'+filesUsr
                            for linesFile in fileAdmin.readlines():
                                check_files.write(linesFile.replace('\n','')+'\t'+lfiles[filesUsr]+'\n')
                            fileAdmin.close()
                    check_files.close()
                    
        
                    dico ={
                        'id' : asso_id['Si'+str(signature_id)],
                        'studies' : asso_id['St'+str(study_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'projects' : studies['St'+str(study_id)]['projects'] ,
                        'title' : projectName+" - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the rat",
                        'type' : 'Genomic',
                        'organism' : 'Rattus norvegicus',
                        'developmental_stage' : 'Adulthood',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'last_update' : str(ztime),
                        'tissue' : tissue_name,
                        'cell' : '',
                        'status' : 'public',
                        'cell_line' : "",
                        'molecule' : "",
                        'pathology' : "",
                        'technology' : 'Microarray',
                        'plateform' : 'GPL1355',
                        'observed_effect' : '',
                        'control_sample' : dSample[condName][0],
                        'treated_sample' : dSample[condName][1],
                        'pvalue' : '0.05',
                        'cutoff' : '1,5',
                        'statistical_processing' : 'Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.',
                        'additional_file' : "",
                        'file_up' : upfile,
                        'file_down' : downfile,
                        'file_interrogated' : interofile,
                        'genes_identifier': 'Entrez genes',
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'unexposed' : "",
                        'exposed' : "",
                        'significance_stat' : "",
                        'stat_value' : "",
                        'stat_adjustments' : "",
                        'stat_other' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Si'+str(signature_id),
                        'genes_up' : ','.join(geneup),
                        'genes_down' : ','.join(genedown)
                    }
                    signatures['Si'+str(signature_id)] = dico
                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    signature_worksheet.write('A6', 'Signature Id')
                    signature_worksheet.write('B6', 'Associated study')
                    signature_worksheet.write('C6', 'Associated assay')
                    signature_worksheet.write('D6', 'Title')
                    signature_worksheet.write('E6', 'Signature type')
                    signature_worksheet.write('F6', 'Organism')
                    signature_worksheet.write('G6', 'Developmental stage')
                    signature_worksheet.write('H6', 'Generation')
                    signature_worksheet.write('I6', 'Sex')
                    signature_worksheet.write('J6', 'Tissue')
                    signature_worksheet.write('K6', 'Cell')
                    signature_worksheet.write('L6', 'Cell Line')
                    signature_worksheet.write('M6', 'Molecule')
                    signature_worksheet.write('N6', 'Associated phenotype, diseases processes or pathway / outcome')
                    signature_worksheet.write('O6', 'Technology used')
                    signature_worksheet.write('P6', 'Plateform')
                    signature_worksheet.write('Q6', 'controle / unexposed (n=)')
                    signature_worksheet.write('R6', 'case / exposed (n=)')
                    signature_worksheet.write('S6', 'Observed effect')
                    signature_worksheet.write('T6', 'Statistical significance')
                    signature_worksheet.write('U6', 'Satistical value')
                    signature_worksheet.write('V6', 'Statistical adjustments')
                    signature_worksheet.write('W6', 'Other satistical information')
                    signature_worksheet.write('X6', 'Control sample')
                    signature_worksheet.write('Y6', 'Treated sample')
                    signature_worksheet.write('Z6', 'pvalue')
                    signature_worksheet.write('AA6', 'Cutoff')
                    signature_worksheet.write('AB6', 'Statistical processing')
                    signature_worksheet.write('AC6', 'Additional file')
                    signature_worksheet.write('AD6', 'File up')
                    signature_worksheet.write('AE6', 'File down')
                    signature_worksheet.write('AF6', 'Interrogated genes file')
                    
                    signature_worksheet.write('A'+str(title_line + signature_id), 'Si'+str(signature_id))
                    signature_worksheet.write('B'+str(title_line + signature_id), 'St'+str(study_id))
                    signature_worksheet.write('C'+str(title_line + signature_id), 'As'+str(assay_id))
                    signature_worksheet.write('D'+str(title_line + signature_id), projectName+"  - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the rat")
                    signature_worksheet.write('E'+str(title_line + signature_id), 'Genomic')
                    signature_worksheet.write('F'+str(title_line + signature_id), 'Rattus norvegicus')
                    signature_worksheet.write('G'+str(title_line + signature_id), "Adulthood")
                    signature_worksheet.write('H'+str(title_line + signature_id), "f0")
                    signature_worksheet.write('I'+str(title_line + signature_id), "Male")
                    signature_worksheet.write('J'+str(title_line + signature_id), tissue_name)
                    signature_worksheet.write('K'+str(title_line + signature_id), "")
                    signature_worksheet.write('L'+str(title_line + signature_id), "")
                    signature_worksheet.write('M'+str(title_line + signature_id), "")
                    signature_worksheet.write('N'+str(title_line + signature_id), "")
                    signature_worksheet.write('O'+str(title_line + signature_id), 'OBI:0400147')
                    signature_worksheet.write('P'+str(title_line + signature_id), 'GPL1355')
                    signature_worksheet.write('Q'+str(title_line + signature_id), "")
                    signature_worksheet.write('R'+str(title_line + signature_id), "")
                    signature_worksheet.write('S'+str(title_line + signature_id), "")
                    signature_worksheet.write('T'+str(title_line + signature_id), "")
                    signature_worksheet.write('U'+str(title_line + signature_id), "")
                    signature_worksheet.write('V'+str(title_line + signature_id), "")
                    signature_worksheet.write('W'+str(title_line + signature_id), "")
                    signature_worksheet.write('X'+str(title_line + signature_id), dSample[condName][0])
                    signature_worksheet.write('Y'+str(title_line + signature_id), dSample[condName][1])
                    signature_worksheet.write('Z'+str(title_line + signature_id), '0.05')
                    signature_worksheet.write('AA'+str(title_line + signature_id), '1.5')
                    signature_worksheet.write('AB'+str(title_line + signature_id), 'Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.')
                    signature_worksheet.write('AC'+str(title_line + signature_id), "")
                    signature_worksheet.write('AD'+str(title_line + signature_id), upfile)
                    signature_worksheet.write('AE'+str(title_line + signature_id), downfile)
                    signature_worksheet.write('AF'+str(title_line + signature_id), interofile)
        workbook.close()

        for proj in projects :
            ID = projects[proj]['id']
            projects[proj]['edges']  = {}
            for stud in studies:
                projects[proj]['edges'][studies[stud]['id']] = studies[stud]['assays'].split()
            for ass in assays:
                projects[proj]['edges'][assays[ass]['id']] = assays[ass]['signatures'].split()

            projects[proj]['edges'] = json.dumps(projects[proj]['edges'])
            db['projects'].insert(projects[proj])
            del projects[proj]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+projects[proj]['id']+"\" } }\n"
            bulk_insert += json.dumps(projects[proj])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for stud in studies:
            db['studies'].insert(studies[stud])
            del studies[stud]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+studies[stud]['id']+"\" } }\n"
            bulk_insert += json.dumps(studies[stud])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for ass in assays:
            db['assays'].insert(assays[ass])
            del assays[ass]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assays[ass]['id']+"\" } }\n"
            bulk_insert += json.dumps(assays[ass])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for fac in factors:
            db['factors'].insert(factors[fac])
            del factors[fac]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"factors\" , \"_id\" : \""+factors[fac]['id']+"\" } }\n"
            bulk_insert += json.dumps(factors[fac])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)


        for sign in signatures:
            db['signatures'].insert(signatures[sign])
            del signatures[sign]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signatures[sign]['id']+"\" } }\n"
            bulk_insert += json.dumps(signatures[sign])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)








def insertTGGATE():
    """
        Insert signatures extrated from ChemPSY processing
        To insert informations please make sur that the following repository is correctlly filled :
            - all_genes_converted files
            - Conditions repository with all individuals conditions
            - Description.txt file
            - projectName.txt file 
            - Studies directory
        This function also required :
            - Individual sample file (Data/files/ChemPSySampleNumber.txt)
            - ChemPSy_MESH.tsv file (Data/files/ChemPSy_MESH.tsv)
    """
    logger.debug('InsertDM - Load dictionnaries')
    projectPath = tggate_path
    projectName = 'TGGATE'
    dChemical = dicoCAS()
    dDataset = {}
    dRoute = dicoRoute(tggate_path+'/'+projectName)
    dCAS = dicoCAS()
    dSample=dicoSample()
    dName = {}
    
    nb_dataset = 0
    nb_study = 0
    nb_cond = 0
    
    orga = toxOrg('TGGATE')




    #DEFINITION DES CONDITIONS PAR CHEMICAL
    logger.debug('InsertDM - Create dico condition')
    for files in os.listdir(projectPath+'Conditions'):
        name = files.replace('_down.txt','').replace('_up.txt','').replace('_noeffects.txt','')
        if 'TGGATE' in name :
            if name not in dDataset :
                dDataset[name] =[]



    logger.debug('InsertDM - Insert project')
    for project in orga :
        if project == "1pc cholesterol and 0.25pc sodium cholate":
            continue
        logger.info(project)
        #print project
        project_id = 0
        study_id = 0
        assay_id = 0
        factor_id = 0
        signature_id = 0
        projects = {}
        studies = {}
        assays = {}
        factors = {}
        signatures = {}
        asso_id = {}
        reverse_asso = {}
        
        
        
        project_id += 1
        
        Dataset_authors = 'Hiroshi Yamada'
        Dataset_email = 'h-yamada@nibio.go.jp'
        Dataset_conditions = []
        Dataset_contributors=['TOXsIgN Team']
        Dataset_pubmed = ['25313160']
        Dataset_extlink = "https://www.nibiohn.go.jp/english/part/fundamental/detail13.html,http://toxico.nibiohn.go.jp/english/"
        Dataset_description = "Open TG-GATEs is a public toxicogenomics database developed so that a wider community of researchers could utilize the fruits of TGP and TGP2 research. This database provides public access to data on 170 of the compounds catalogued in TG-GATEs. Data searching can be refined using either the name of a compound or the pathological findings by organ as the starting point. Gene expression data linked to phenotype data in pathology findings can also be downloaded as a CEL(*)file. "
        Dataset_owner = 'h-yamada@nibio.go.jp'
        Dataset_status = "public"
        Dataset_ID = 'TSP' + str(get_Index('project'))
        Dataset_title = "Open TG-GATEs - Toxicogenomic signatures after exposure to "+project+" in the rat"

        # DATASET CREATION
        dt = datetime.datetime.utcnow()
        ztime = mktime(dt.timetuple())
        dico={
                'id' : Dataset_ID,
                'title' : Dataset_title,
                'description' : Dataset_description,
                'pubmed' : ','.join(Dataset_pubmed),
                'contributor' : ','.join(Dataset_contributors),
                'assays' : "",
                'cross_link':Dataset_extlink,
                'studies' : "",
                'factors' : "",
                'signatures' :"",
                'last_update' : str(ztime),
                'submission_date' : str(ztime),
                'status' : 'public' ,
                'owner' : Dataset_owner,
                'author' : Dataset_authors ,
                'tags' : "",
                'edges' : "",
                'info' : "",
                'warnings' : "",
                'critical' : "",
                'excel_id' : 'PR'+str(project_id)
            }
        
        #Add to dico
        print "########################    PROJECT    ########################"
        asso_id['PR'+str(project_id)] = Dataset_ID
        print asso_id['PR'+str(project_id)]
        reverse_asso[asso_id['PR'+str(project_id)]] = 'PR'+str(project_id)
        projects['PR'+str(project_id)] = dico
        print "###############################################################"
        
        
        nb_dataset = nb_dataset + 1
        
        
        #Create project excel
        title_line = 5 
        project_path = os.path.join(public_path,Dataset_ID)
        os.makedirs(project_path)



        workbook = xlsxwriter.Workbook(project_path+'/TOXsIgN_'+Dataset_ID+'.xlsx')
        project_worksheet = workbook.add_worksheet('Projects')
        study_worksheet = workbook.add_worksheet('Studies')
        asssay_worksheet = workbook.add_worksheet('Assays')
        factor_worksheet = workbook.add_worksheet('Factors')
        signature_worksheet = workbook.add_worksheet('Signatures')
        project_worksheet.write('A1', '# TOXsIgN - Excel template version 0.3')
        project_worksheet.write('C1', '# Fill the project description')
        project_worksheet.write('C2', '# Each project is defined by one unique title (one by line)')
        project_worksheet.write('C3', '# A project is the global description of your studies')
        project_worksheet.write('A5', 'Project Id')
        project_worksheet.write('B5', 'Title')
        project_worksheet.write('C5', 'Description')
        project_worksheet.write('D5', 'PubMed Id(s) (comma separated)')
        project_worksheet.write('E5', 'Contributors (comma separated)')
        project_worksheet.write('A'+str(title_line + project_id), 'PR'+str(project_id))
        project_worksheet.write('B'+str(title_line + project_id), Dataset_title)
        project_worksheet.write('C'+str(title_line + project_id), Dataset_description)
        project_worksheet.write('D'+str(title_line + project_id), ','.join(Dataset_pubmed))
        project_worksheet.write('E'+str(title_line + project_id), ','.join(Dataset_contributors))
        
        organeList = ['LIVER','KIDNEY']
        for studorg in organeList  :
            if studorg in orga[project]:
                study_id += 1


                study = studorg
                #print study


                tissue_name = ''
                tissue_ID = ''
                study_description = ''
                if study == 'LIVER' :
                    tissue_name = 'Liver'
                    tissue_ID = 'FMA:7197'
                    study_description = "Complete Open TG-GATEs dataset for rat liver."
                if study == 'KIDNEY' :
                    tissue_name = 'Kidney'
                    tissue_ID = 'FMA:7203'
                    study_description = "Complete Open TG-GATEs dataset for rat kidney."
                if study == 'HEART' :
                    tissue_name = 'Heart'
                    tissue_ID = 'FMA:7088'
                    study_description = "Complete Open TG-GATEs dataset for rat heart."
                if study == 'THIGH-MUSCLE' :
                    tissue_name = 'Skeletal muscle tissue'
                    tissue_ID = 'FMA:14069'
                    study_description = "Complete Open TG-GATEs dataset for rat thigh muscle."
                


                print "########################    Study    ########################"
                study_projects = 'PR'+str(project_id)
                #Excel id -> databas id
                asso_id['St'+str(study_id)] = 'TSE' + str(get_Index('study'))
                print asso_id['St'+str(study_id)]
                reverse_asso[asso_id['St'+str(study_id)]] = study_id
    
                #Add studies id to associated project
                p_stud = projects[study_projects]['studies'].split()
                p_stud.append(asso_id['St'+str(study_id)])
                projects[study_projects]['studies'] = ','.join(p_stud)
                print "add to " + study_projects + "----> " + str(p_stud)
                print "###############################################################"
    
                dico={
                    'id' : asso_id['St'+str(study_id)],
                    'owner' : Dataset_owner,
                    'projects' : asso_id['PR'+str(project_id)],
                    'assays' : "",
                    'factors' : "",
                    'signatures' : "",
                    'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the rat",
                    'description' : study_description,
                    'experimental_design' : "Animal experiments were conducted by four different contract research organizations. The studies used male Crl:CD Sprague-Dawley (SD) rats purchased from Charles River Japan, Inc. (Hino or Atsugi, Japan) as 5-week-old animals. After a 7-day quarantine and acclimatization period, the animals were allocated into groups of 20 animals each using a computerized stratified random grouping method based on body weight. Each animal was allowed free access to water and pelleted food (radiation-sterilized CRF-1; Oriental Yeast Co., Tokyo, Japan). For single-dose experiments, groups of 20 animals were administered a compound and then fivw animals/time point were sacrificed at 3, 6, 9 or 24 h after administration. For repeated-dose experiments, groups of 20 animals received a single dose per day of a compound and five animals/time point were sacrificed at 4, 8, 15 or 29 days (i.e. 24 h after the respective final administration at 3, 7, 14 or 28 days). Animals were not fasted before being sacrificed. To avoid effects of diurnal cycling, the animals were sacrificed and necropsies were performed between 9:00 a.m. and 11:00 a.m. for the repeated-dose studies. Blood samples for routine biochemical analyses were collected into heparinized tubes under ether anesthesia from the abdominal aorta at the time of sacrifice.",
                    'results' : "",
                    'study_type' : 'Interventional',
                    'last_update' : str(ztime),
                    'inclusion_period': "",
                    'inclusion': "",
                    'exclusion': "",
                    'status' : 'public',
                    'followup': "",
                    'population_size' : "",
                    'pubmed' : "",
                    'tags' : "",
                    'info' : "",
                    'warnings' : "",
                    'critical' : "",
                    'excel_id' : 'St'+str(study_id)
                }      
                
                studies['St'+str(study_id)]=dico
                
                #Create study excel
                title_line = 6 
                
                format = workbook.add_format()
                format.set_pattern(1)  # This is optional when using a solid fill.
                format.set_bg_color('green')

                study_worksheet.write('C1', '# Fill the study description')
                study_worksheet.write('C2', '# Each study is defined by one unique title (one by line) need to be associated with only one project')
                study_worksheet.write('C3', '# A study is the detail description of your experimentations')
                study_worksheet.write('C4', 'Only for observational studies',format)
                
                study_worksheet.write('A6', 'Study Id')
                study_worksheet.write('B6', 'Associated project')
                study_worksheet.write('C6', 'Study Title')
                study_worksheet.write('D6', 'Description')
                study_worksheet.write('E6', 'Design')
                study_worksheet.write('F6', 'Results')
                study_worksheet.write('G6', 'Study type ')
                study_worksheet.write('H6', 'Inclusion period')
                study_worksheet.write('I6', 'Inclusion criteria')
                study_worksheet.write('J6', 'Exclusion criteria')
                study_worksheet.write('K6', 'Follow up')
                study_worksheet.write('L6', 'Pubmed Id(s) (comma separated)')
                study_worksheet.write('M6', 'Interventional')
                
                study_worksheet.write('A'+str(title_line + study_id), 'St'+str(study_id))
                study_worksheet.write('B'+str(title_line + study_id), 'PR'+str(project_id))
                study_worksheet.write('C'+str(title_line + study_id), "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the rat")
                study_worksheet.write('D'+str(title_line + study_id), study_description)
                study_worksheet.write('E'+str(title_line + study_id), str("Animal experiments were conducted by four different contract research organizations. The studies used male Crl:CD Sprague-Dawley (SD) rats purchased from Charles River Japan, Inc. (Hino or Atsugi, Japan) as 5-week-old animals. After a 7-day quarantine and acclimatization period, the animals were allocated into groups of 20 animals each using a computerized stratified random grouping method based on body weight. Each animal was allowed free access to water and pelleted food (radiation-sterilized CRF-1; Oriental Yeast Co., Tokyo, Japan). For single-dose experiments, groups of 20 animals were administered a compound and then fivw animals/time point were sacrificed at 3, 6, 9 or 24 h after administration. For repeated-dose experiments, groups of 20 animals received a single dose per day of a compound and five animals/time point were sacrificed at 4, 8, 15 or 29 days (i.e. 24 h after the respective final administration at 3, 7, 14 or 28 days). Animals were not fasted before being sacrificed. To avoid effects of diurnal cycling, the animals were sacrificed and necropsies were performed between 9:00 a.m. and 11:00 a.m. for the repeated-dose studies. Blood samples for routine biochemical analyses were collected into heparinized tubes under ether anesthesia from the abdominal aorta at the time of sacrifice.").decode('utf-8') )
                study_worksheet.write('F'+str(title_line + study_id), "")
                study_worksheet.write('G'+str(title_line + study_id), "")
                
                
                for cond in orga[project][studorg] :
                    assay_id += 1
                    dose = cond.split('+')[0]
                    print cond
                    temps = cond.split('+')[1]
                    print temps
                     #CREATION INFORMATION CONDITION

                     #RECUPERATION NOM | CAS | ROUTE DU CHEMICAL
                    condName = orga[project][studorg][cond]
                    prezfile = 1
                    if condName in dDataset :
                        upFile = open(projectPath+'Conditions/'+condName+'_up.txt','r')
                        downFile = open(projectPath+'Conditions/'+condName+'_down.txt','r')
                    else :
                        prezfile = 0

                    CAS = getFileCas(condName)
                    dCas = getCAS()
                    if CAS.rstrip() not in dCas :
                        chemName = files.split('+')[2]+' CAS:NA'
                        chemID = ""
                    else :
                        chemName = dCas[CAS.rstrip()][0]
                        chemID = dCas[CAS.rstrip()][1]
                    chemRoute = ""
                    if condName in dCAS :
                        if dCAS[condName] in dRoute :
                            chemRoute = dRoute[dCAS[condName]]
                        else :
                            chemRoute = "other"
                    
    
                   
                    if chemID != "" :
                         chemtag = get_tag('chemical.tab',chemID)
                    else : 
                        chemtag =chemName
                  
                    doses = dose.split('_')[0]
                    dose_unit = dose.split('_')[1].replace('mgkg','mg/kg')
                    exposure = temps.split('_')[0]
                    exposure_unit = temps.split('_')[1]
                    timeexpo = 0
                    # CHANGE TIME UNIT
                    if exposure_unit == 'd' :
                        exposure_unit = "days"
                        timeexpo = float(exposure) * 1440
                    if exposure_unit == 'hr' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'h' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'min' :
                        exposure_unit = "minutes"
                        timeexpo = float(exposure) * 1
                        
                    #Excel id -> databas id
                    asso_id['As'+str(assay_id)] = 'TSA'+str(get_Index('assay'))
                    reverse_asso[asso_id['As'+str(assay_id)]] = 'As'+str(assay_id)
        
                    #Add assay id to associated study
                    s_assay = studies['St'+str(study_id)]['assays'].split()
                    s_assay.append(asso_id['As'+str(assay_id)])
                    studies['St'+str(study_id)]['assays'] = ','.join(s_assay)
        
                    #Add assay to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
                    print project_asso
        
                    p_assay = projects['PR'+str(project_id)]['assays'].split()
                    p_assay.append(asso_id['As'+str(assay_id)])
                    projects['PR'+str(project_id)]['assays'] = ','.join(p_assay)
        
                    #After reading line add all info in dico project
                    tag = get_tag('species.tab','NCBITaxon:10116')
                    tissue_tag = get_tag('tissue.tab',tissue_ID)
                    tag.extend(tissue_tag)
                    
                    dico={
                        'id' : asso_id['As'+str(assay_id)] ,
                        'studies' : asso_id['St'+str(study_id)],
                        'factors' : "",
                        'signatures' : "",
                        'projects' : studies['St'+str(study_id)]['projects'],
                        'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+str(doses)+" "+dose_unit+", "+str(exposure)+" "+exposure_unit+") in the rat",
                        'organism' : 'Rattus norvegicus',
                        'experimental_type' : 'in vivo',
                        'developmental_stage' : 'Adulthood',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'tissue' : tissue_name,
                        'cell' : "",
                        'status' : 'public',
                        'last_update' : str(ztime),
                        'cell_line' : "",
                        'additional_information' : "",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'As'+str(assay_id),
                        'pop_age' : "",
                        'location': "",
                        'reference' : "",
                        'matrice' : ""
                    }
                    assays['As'+str(assay_id)] = dico
                    
                    #Create study excel
                    title_line = 12 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    asssay_worksheet.write('A12', 'Assay Id')
                    asssay_worksheet.write('B12', 'Associated study')
                    asssay_worksheet.write('C12', 'Title')
                    asssay_worksheet.write('D12', 'Organism')
                    asssay_worksheet.write('E12', 'Developmental stage')
                    asssay_worksheet.write('F12', 'Generation')
                    asssay_worksheet.write('G12', 'Sex')
                    asssay_worksheet.write('H12', 'Tissue')
                    asssay_worksheet.write('I12', 'Cell')
                    asssay_worksheet.write('J12', 'Cell Line')
                    asssay_worksheet.write('K12', 'Experimental type')
                    asssay_worksheet.write('L12', 'Additional information')
                    asssay_worksheet.write('M12', 'Population age')
                    asssay_worksheet.write('N12', 'Geographical location')
                    asssay_worksheet.write('O12', 'Controle / Reference')
                    asssay_worksheet.write('P12', 'Biological matrice')
                    
                    asssay_worksheet.write('A'+str(title_line + assay_id), 'As'+str(assay_id))
                    asssay_worksheet.write('B'+str(title_line + assay_id), 'St'+str(study_id))
                    asssay_worksheet.write('C'+str(title_line + assay_id), "Open TG-GATE  - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+str(doses)+" "+dose_unit+", "+str(exposure)+" "+exposure_unit+") in the rat")
                    asssay_worksheet.write('D'+str(title_line + assay_id), 'NCBITaxon:10116')
                    asssay_worksheet.write('E'+str(title_line + assay_id), 'Adulthood')
                    asssay_worksheet.write('F'+str(title_line + assay_id), "f0")
                    asssay_worksheet.write('G'+str(title_line + assay_id), "Male")
                    asssay_worksheet.write('H'+str(title_line + assay_id), tissue_ID)
                    asssay_worksheet.write('K'+str(title_line + assay_id), 'in vivo')
                    
                    factor_id += 1
                                        
                    
                    #Excel id -> databas id
                    asso_id['Fc'+str(factor_id)] = 'TSF'+str(get_Index('factor'))
                    reverse_asso[asso_id['Fc'+str(factor_id)]] = 'Fc'+str(factor_id)
        
                    #Add factor id to associated assay
                    a_factor = assays['As'+str(assay_id)]['factors'].split()
                    a_factor.append(asso_id['Fc'+str(factor_id)])
                    assays['As'+str(assay_id)]['factors'] = ','.join(a_factor)
        
                    #Add factor to the associated study
                    study_asso = reverse_asso[assays['As'+str(assay_id)]['studies']]
        
                    s_factor = studies['St'+str(study_id)]['factors'].split()
                    s_factor.append(asso_id['Fc'+str(factor_id)])
                    studies['St'+str(study_id)]['factors'] = ','.join(s_factor)
        
                    #Add factor to the associated project
                    project_asso = assays['As'+str(assay_id)]['projects']
        
                    p_factor = projects['PR'+str(project_id)]['factors'].split()
                    p_factor.append(asso_id['Fc'+str(factor_id)])
                    projects['PR'+str(project_id)]['factors'] = ','.join(p_factor)

                    tag.extend(chemtag)
                    myset = list(set(tag))
                    tag = myset
        

        
                    #After reading line add all info in dico project
                    dico={
                        'id' : asso_id['Fc'+str(factor_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'studies' : assays['As'+str(assay_id)]['studies'],
                        'project' : assays['As'+str(assay_id)]['projects'],
                        'type' : "Chemical",
                        'chemical' : chemName,
                        'physical' : "",
                        'biological' : "",
                        'route' : chemRoute,
                        'last_update' : str(ztime),
                        'status' : 'public',
                        'vehicle' : 'NA',
                        'dose' : str(doses) +" "+ dose_unit,
                        'exposure_duration' : str(exposure) +" "+ exposure_unit,
                        'exposure_frequencies' : "",
                        'additional_information' : "The 0.25 and 1-day time points were harvested starting at 1:00 p.m. and completed within 1–2 h, whereas the 3 and 5-day time points were harvested starting at 7:00 a.m. and completed within 2–4 h; all harvests used an appropriately staggered schedule so that the harvest times were accurate to 30 min of the designed dose-to-harvest interval.",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Fc'+str(factor_id)
                    }
                    factors['Fc'+str(factor_id)] = dico


                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    factor_worksheet.write('A6', 'Factor Id')
                    factor_worksheet.write('B6', 'Associated assay')
                    factor_worksheet.write('C6', 'Exposition factor')
                    factor_worksheet.write('D6', 'Chemical name')
                    factor_worksheet.write('E6', 'Physical')
                    factor_worksheet.write('F6', 'Biological')
                    factor_worksheet.write('G6', 'Route')
                    factor_worksheet.write('H6', 'Vehicle')
                    factor_worksheet.write('I6', 'Dose')
                    factor_worksheet.write('J6', 'Dose unit')
                    factor_worksheet.write('K6', 'Exposure duration')
                    factor_worksheet.write('L6', 'Exposure duration unit')
                    factor_worksheet.write('M6', 'Exposure frequecies')
                    factor_worksheet.write('N6', 'Additional information')

                    
                    factor_worksheet.write('A'+str(title_line + factor_id), 'Fc'+str(factor_id))
                    factor_worksheet.write('B'+str(title_line + factor_id), 'As'+str(assay_id))
                    factor_worksheet.write('C'+str(title_line + factor_id), "Chemical")
                    factor_worksheet.write('D'+str(title_line + factor_id), chemName)
                    factor_worksheet.write('E'+str(title_line + factor_id), "")
                    factor_worksheet.write('F'+str(title_line + factor_id), "")
                    factor_worksheet.write('G'+str(title_line + factor_id), chemRoute)
                    factor_worksheet.write('H'+str(title_line + factor_id), 'NA')
                    factor_worksheet.write('I'+str(title_line + factor_id), str(doses))
                    factor_worksheet.write('J'+str(title_line + factor_id), dose_unit)
                    factor_worksheet.write('K'+str(title_line + factor_id), str(exposure))
                    factor_worksheet.write('L'+str(title_line + factor_id), exposure_unit)
                    factor_worksheet.write('M'+str(title_line + factor_id), '')
                    factor_worksheet.write('N'+str(title_line + factor_id), str("The 0.25 and 1-day time points were harvested starting at 1:00 p.m. and completed within 1–2 h, whereas the 3 and 5-day time points were harvested starting at 7:00 a.m. and completed within 2–4 h; all harvests used an appropriately staggered schedule so that the harvest times were accurate to 30 min of the designed dose-to-harvest interval.").decode('utf-8'))
                    
                    
                    signature_id += 1
                    
                    #Excel id -> databas id
                    asso_id['Si'+str(signature_id)] = 'TSS'+str(get_Index('signature'))
                    reverse_asso[asso_id['Si'+str(signature_id)]] = 'Si'+str(signature_id)
        
                    #Add signature id to associated assay
                    a_signature = assays['As'+str(assay_id)]['signatures'].split()
        
                    a_signature.append(asso_id['Si'+str(signature_id)])
                    assays['As'+str(assay_id)]['signatures'] = ','.join(a_signature)
        
                    #Add factor to the associated study
        
                    s_signature = studies['St'+str(study_id)]['signatures'].split()
                    s_signature.append(asso_id['Si'+str(signature_id)])
                    studies['St'+str(study_id)]['signatures'] = ','.join(s_signature)
        
                    #Add factor to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
        
                    p_signature = projects['PR'+str(project_id)]['signatures'].split()
                    p_signature.append(asso_id['Si'+str(signature_id)])
                    projects['PR'+str(project_id)]['signatures'] = ','.join(p_signature)
        
                    #get factors
                    tag.extend(get_tag('experiment.tab','OBI:0400147'))
                    myset = list(set(tag))
                    tag = myset
                    
                    
                   
                   
                    dirCond = public_path+Dataset_ID+"/"+asso_id['Si'+str(signature_id)]
                    geneup = []
                    genedown = []
                    interofile =""
                    file_up = ""
                    file_down = ""
                    upfile = ""
                    downfile = ""
                
                    os.makedirs(dirCond)
                    if prezfile == 1:
                        upfile = condName+'_up.txt'
                        print upfile
                        lId = []
                        for idline in upFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            geneup.append(idline.replace('\n',''))
                        lId = list(set(lId))
                        upFile.close()
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_up.txt')):
                            os.remove(os.path.join(dirCond,condName+'_up.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_up.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                
                        check_files.close()
                        
                        
                        
                        downfile = condName+'_down.txt'
                        print downfile
                        lId = []
                        for idline in downFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            genedown.append(idline.replace('\n',''))
                        downFile.close()
                        lId = list(set(lId))
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_down.txt')):
                            os.remove(os.path.join(dirCond,condName+'_down.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_down.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                  
                        check_files.close() 
               
            
                        
                        
                        
                    if os.path.isfile(os.path.join(dirCond,'genomic_interrogated_genes.txt')):
                        os.remove(os.path.join(dirCond,'genomic_interrogated_genes.txt'))
                    interofile = 'genomic_interrogated_genes.txt'
                    cmd3 = 'cp %s %s' % (projectPath+'all_genes_converted.txt',dirCond+'/genomic_interrogated_genes.txt')
                    os.system(cmd3)
                    
                    
                    
                    upload_path = admin_path
                    all_name = asso_id['Si'+str(signature_id)]+'.sign'
                    adm_path_signame = os.path.join(upload_path,'signatures_data',all_name)
                    #admin
                    if not os.path.exists(os.path.join(upload_path,'signatures_data')):
                        os.makedirs(os.path.join(upload_path,'signatures_data'))
                    if os.path.isfile(adm_path_signame):
                        os.remove(adm_path_signame)
                
                    check_files = open(adm_path_signame,'a')
                    lfiles = {'genomic_upward.txt':'1','genomic_downward.txt':'-1','genomic_interrogated_genes.txt':'0'}
                    val_geno = 0
                    for filesUsr in os.listdir(dirCond) :
                        if filesUsr in lfiles:
                            fileAdmin = open(dirCond +'/'+filesUsr,'r')
                            print dirCond +'/'+filesUsr
                            for linesFile in fileAdmin.readlines():
                                check_files.write(linesFile.replace('\n','')+'\t'+lfiles[filesUsr]+'\n')
                            fileAdmin.close()
                    check_files.close()
                    
        
                    dico ={
                        'id' : asso_id['Si'+str(signature_id)],
                        'studies' : asso_id['St'+str(study_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'projects' : studies['St'+str(study_id)]['projects'] ,
                        'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+str(doses)+" "+dose_unit+", "+str(exposure)+" "+exposure_unit+") in the rat",
                        'type' : 'Genomic',
                        'organism' : 'Rattus norvegicus',
                        'developmental_stage' : 'Adulthood',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'last_update' : str(ztime),
                        'tissue' : tissue_name,
                        'cell' : '',
                        'status' : 'public',
                        'cell_line' : "",
                        'molecule' : "",
                        'pathology' : "",
                        'technology' : 'Microarray',
                        'plateform' : 'GPL1355',
                        'observed_effect' : '',
                        'control_sample' : str(dSample[condName][0]),
                        'treated_sample' : str(dSample[condName][1]),
                        'pvalue' : '0.05',
                        'cutoff' : '1,5',
                        'study_type':'Interventional',
                        'statistical_processing' : 'Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.',
                        'additional_file' : "",
                        'file_up' : upfile,
                        'file_down' : downfile,
                        'file_interrogated' : interofile,
                        'genes_identifier': 'Entrez genes',
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'unexposed' : "",
                        'exposed' : "",
                        'significance_stat' : "",
                        'stat_value' : "",
                        'stat_adjustments' : "",
                        'stat_other' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Si'+str(signature_id),
                        'genes_up' : ','.join(geneup),
                        'genes_down' : ','.join(genedown)
                    }
                    signatures['Si'+str(signature_id)] = dico
                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    signature_worksheet.write('A6', 'Signature Id')
                    signature_worksheet.write('B6', 'Associated study')
                    signature_worksheet.write('C6', 'Associated assay')
                    signature_worksheet.write('D6', 'Title')
                    signature_worksheet.write('E6', 'Signature type')
                    signature_worksheet.write('F6', 'Organism')
                    signature_worksheet.write('G6', 'Developmental stage')
                    signature_worksheet.write('H6', 'Generation')
                    signature_worksheet.write('I6', 'Sex')
                    signature_worksheet.write('J6', 'Tissue')
                    signature_worksheet.write('K6', 'Cell')
                    signature_worksheet.write('L6', 'Cell Line')
                    signature_worksheet.write('M6', 'Molecule')
                    signature_worksheet.write('N6', 'Associated phenotype, diseases processes or pathway / outcome')
                    signature_worksheet.write('O6', 'Technology used')
                    signature_worksheet.write('P6', 'Plateform')
                    signature_worksheet.write('Q6', 'controle / unexposed (n=)')
                    signature_worksheet.write('R6', 'case / exposed (n=)')
                    signature_worksheet.write('S6', 'Observed effect')
                    signature_worksheet.write('T6', 'Statistical significance')
                    signature_worksheet.write('U6', 'Satistical value')
                    signature_worksheet.write('V6', 'Statistical adjustments')
                    signature_worksheet.write('W6', 'Other satistical information')
                    signature_worksheet.write('X6', 'Control sample')
                    signature_worksheet.write('Y6', 'Treated sample')
                    signature_worksheet.write('Z6', 'pvalue')
                    signature_worksheet.write('AA6', 'Cutoff')
                    signature_worksheet.write('AB6', 'Statistical processing')
                    signature_worksheet.write('AC6', 'Additional file')
                    signature_worksheet.write('AD6', 'File up')
                    signature_worksheet.write('AE6', 'File down')
                    signature_worksheet.write('AF6', 'Interrogated genes file')
                    
                    signature_worksheet.write('A'+str(title_line + signature_id), 'Si'+str(signature_id))
                    signature_worksheet.write('B'+str(title_line + signature_id), 'St'+str(study_id))
                    signature_worksheet.write('C'+str(title_line + signature_id), 'As'+str(assay_id))
                    signature_worksheet.write('D'+str(title_line + signature_id), "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+str(doses)+" "+dose_unit+", "+str(exposure)+" "+exposure_unit+") in the rat")
                    signature_worksheet.write('E'+str(title_line + signature_id), 'Genomic')
                    signature_worksheet.write('F'+str(title_line + signature_id), 'Rattus norvegicus')
                    signature_worksheet.write('G'+str(title_line + signature_id), "Adulthood")
                    signature_worksheet.write('H'+str(title_line + signature_id), "f0")
                    signature_worksheet.write('I'+str(title_line + signature_id), "Male")
                    signature_worksheet.write('J'+str(title_line + signature_id), tissue_name)
                    signature_worksheet.write('K'+str(title_line + signature_id), "")
                    signature_worksheet.write('L'+str(title_line + signature_id), "")
                    signature_worksheet.write('M'+str(title_line + signature_id), "")
                    signature_worksheet.write('N'+str(title_line + signature_id), "")
                    signature_worksheet.write('O'+str(title_line + signature_id), 'OBI:0400147')
                    signature_worksheet.write('P'+str(title_line + signature_id), 'GPL1355')
                    signature_worksheet.write('Q'+str(title_line + signature_id), "")
                    signature_worksheet.write('R'+str(title_line + signature_id), "")
                    signature_worksheet.write('S'+str(title_line + signature_id), "")
                    signature_worksheet.write('T'+str(title_line + signature_id), "")
                    signature_worksheet.write('U'+str(title_line + signature_id), "")
                    signature_worksheet.write('V'+str(title_line + signature_id), "")
                    signature_worksheet.write('W'+str(title_line + signature_id), "")
                    signature_worksheet.write('X'+str(title_line + signature_id), str(dSample[condName][0]))
                    signature_worksheet.write('Y'+str(title_line + signature_id), str(dSample[condName][1]))
                    signature_worksheet.write('Z'+str(title_line + signature_id), '0.05')
                    signature_worksheet.write('AA'+str(title_line + signature_id), '1.5')
                    signature_worksheet.write('AB'+str(title_line + signature_id), str('Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.').decode('utf-8'))
                    signature_worksheet.write('AC'+str(title_line + signature_id), "")
                    signature_worksheet.write('AD'+str(title_line + signature_id), upfile)
                    signature_worksheet.write('AE'+str(title_line + signature_id), downfile)
                    signature_worksheet.write('AF'+str(title_line + signature_id), interofile)
        workbook.close()

        for proj in projects :
            ID = projects[proj]['id']
            projects[proj]['edges']  = {}
            for stud in studies:
                projects[proj]['edges'][studies[stud]['id']] = studies[stud]['assays'].split()
            for ass in assays:
                projects[proj]['edges'][assays[ass]['id']] = assays[ass]['signatures'].split()

            projects[proj]['edges'] = json.dumps(projects[proj]['edges'])
            db['projects'].insert(projects[proj])
            del projects[proj]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+projects[proj]['id']+"\" } }\n"
            bulk_insert += json.dumps(projects[proj])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for stud in studies:
            db['studies'].insert(studies[stud])
            del studies[stud]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+studies[stud]['id']+"\" } }\n"
            bulk_insert += json.dumps(studies[stud])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for ass in assays:
            db['assays'].insert(assays[ass])
            del assays[ass]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assays[ass]['id']+"\" } }\n"
            bulk_insert += json.dumps(assays[ass])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for fac in factors:
            db['factors'].insert(factors[fac])
            del factors[fac]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"factors\" , \"_id\" : \""+factors[fac]['id']+"\" } }\n"
            bulk_insert += json.dumps(factors[fac])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)


        for sign in signatures:
            db['signatures'].insert(signatures[sign])
            del signatures[sign]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signatures[sign]['id']+"\" } }\n"
            bulk_insert += json.dumps(signatures[sign])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)
















def insertHumanTG():
    """
        Insert signatures extrated from ChemPSY processing
        To insert informations please make sur that the following repository is correctlly filled :
            - all_genes_converted files
            - Conditions repository with all individuals conditions
            - Description.txt file
            - projectName.txt file 
            - Studies directory
        This function also required :
            - Individual sample file (Data/files/ChemPSySampleNumber.txt)
            - ChemPSy_MESH.tsv file (Data/files/ChemPSy_MESH.tsv)
    """
    logger.debug('insertHumanTG - Load dictionnaries')
    projectPath = tggatehuman_path
    projectName = 'TGGATE_human'
    dChemical = dicoCAS()
    dico_cond = condDico()
    dDataset = {}
    dRoute = dicoRoute(tggatehuman_path+'/'+projectName)
    dCAS = dicoCAS()
    dSample=dicoSampleHuman()
    dName = {}
    
    nb_dataset = 0
    nb_study = 0
    nb_cond = 0
    
    orga = human_toxOrg('TGGATE')




    #DEFINITION DES CONDITIONS PAR CHEMICAL
    logger.debug('InsertDM - Create dico condition')
    for files in os.listdir(projectPath+'Conditions'):
        name = files.replace('_down.txt','').replace('_up.txt','').replace('_noeffects.txt','')
        if 'TGGATE' in name :
            if name not in dDataset :
                dDataset[name] =[]



    logger.debug('InsertDM - Insert project')
    for project in orga :
        if project == "1pc cholesterol and 0.25pc sodium cholate":
            continue
        logger.info(project)
        #print project
        project_id = 0
        study_id = 0
        assay_id = 0
        factor_id = 0
        signature_id = 0
        projects = {}
        studies = {}
        assays = {}
        factors = {}
        signatures = {}
        asso_id = {}
        reverse_asso = {}
        
        
        
        project_id += 1
        
        Dataset_authors = 'Hiroshi Yamada'
        Dataset_email = 'h-yamada@nibio.go.jp'
        Dataset_conditions = []
        Dataset_contributors=['TOXsIgN Team']
        Dataset_pubmed = ['25313160']
        Dataset_extlink = "https://www.nibiohn.go.jp/english/part/fundamental/detail13.html,http://toxico.nibiohn.go.jp/english/"
        Dataset_description = "Open TG-GATEs is a public toxicogenomic database developed so that a wider community of researchers could utilize the fruits of TGP and TGP2 research. This database provides public access to data on 170 of the compounds catalogued in TG-GATEs. Data searching can be refined using either the name of a compound or the pathological findings by organ as the starting point. Gene expression data linked to phenotype data in pathology findings can also be downloaded as a CEL(*)file. "
        Dataset_owner = 'h-yamada@nibio.go.jp'
        Dataset_status = "public"
        Dataset_ID = 'TSP' + str(get_Index('project'))
        Dataset_title = "Open TG-GATEs - Toxicogenomic signatures after exposure to "+project+" in the human"

        # DATASET CREATION
        dt = datetime.datetime.utcnow()
        ztime = mktime(dt.timetuple())
        dico={
                'id' : Dataset_ID,
                'title' : Dataset_title,
                'description' : Dataset_description,
                'pubmed' : ','.join(Dataset_pubmed),
                'contributor' : ','.join(Dataset_contributors),
                'assays' : "",
                'cross_link':Dataset_extlink,
                'studies' : "",
                'factors' : "",
                'signatures' :"",
                'last_update' : str(ztime),
                'submission_date' : str(ztime),
                'status' : 'public' ,
                'owner' : Dataset_owner,
                'author' : Dataset_authors ,
                'tags' : "",
                'edges' : "",
                'info' : "",
                'warnings' : "",
                'critical' : "",
                'excel_id' : 'PR'+str(project_id)
            }
        
        #Add to dico
        print "########################    PROJECT    ########################"
        asso_id['PR'+str(project_id)] = Dataset_ID
        print asso_id['PR'+str(project_id)]
        reverse_asso[asso_id['PR'+str(project_id)]] = 'PR'+str(project_id)
        projects['PR'+str(project_id)] = dico
        print "###############################################################"
        
        
        nb_dataset = nb_dataset + 1
        
        
        #Create project excel
        title_line = 5 
        project_path = os.path.join(public_path,Dataset_ID)
        os.makedirs(project_path)



        workbook = xlsxwriter.Workbook(project_path+'/TOXsIgN_'+Dataset_ID+'.xlsx')
        project_worksheet = workbook.add_worksheet('Projects')
        study_worksheet = workbook.add_worksheet('Studies')
        asssay_worksheet = workbook.add_worksheet('Assays')
        factor_worksheet = workbook.add_worksheet('Factors')
        signature_worksheet = workbook.add_worksheet('Signatures')
        project_worksheet.write('A1', '# TOXsIgN - Excel template version 0.3')
        project_worksheet.write('C1', '# Fill the project description')
        project_worksheet.write('C2', '# Each project is defined by one unique title (one by line)')
        project_worksheet.write('C3', '# A project is the global description of your studies')
        project_worksheet.write('A5', 'Project Id')
        project_worksheet.write('B5', 'Title')
        project_worksheet.write('C5', 'Description')
        project_worksheet.write('D5', 'PubMed Id(s) (comma separated)')
        project_worksheet.write('E5', 'Contributors (comma separated)')
        project_worksheet.write('A'+str(title_line + project_id), 'PR'+str(project_id))
        project_worksheet.write('B'+str(title_line + project_id), Dataset_title)
        project_worksheet.write('C'+str(title_line + project_id), Dataset_description)
        project_worksheet.write('D'+str(title_line + project_id), ','.join(Dataset_pubmed))
        project_worksheet.write('E'+str(title_line + project_id), ','.join(Dataset_contributors))
        
        organeList = ['LIVER','KIDNEY']
        for studorg in organeList  :
            if studorg in orga[project]:
                study_id += 1


                study = studorg
                #print study


                tissue_name = ''
                tissue_ID = ''
                study_description = ''
                if study == 'LIVER' :
                    tissue_name = 'Liver'
                    tissue_ID = 'FMA:7197'
                    study_description = "Complete Open TG-GATEs dataset for rat liver."
                if study == 'KIDNEY' :
                    tissue_name = 'Kidney'
                    tissue_ID = 'FMA:7203'
                    study_description = "Complete Open TG-GATEs dataset for rat kidney."
                if study == 'HEART' :
                    tissue_name = 'Heart'
                    tissue_ID = 'FMA:7088'
                    study_description = "Complete Open TG-GATEs dataset for rat heart."
                if study == 'THIGH-MUSCLE' :
                    tissue_name = 'Skeletal muscle tissue'
                    tissue_ID = 'FMA:14069'
                    study_description = "Complete Open TG-GATEs dataset for rat thigh muscle."
                


                print "########################    Study    ########################"
                study_projects = 'PR'+str(project_id)
                #Excel id -> databas id
                asso_id['St'+str(study_id)] = 'TSE' + str(get_Index('study'))
                print asso_id['St'+str(study_id)]
                reverse_asso[asso_id['St'+str(study_id)]] = study_id
    
                #Add studies id to associated project
                p_stud = projects[study_projects]['studies'].split()
                p_stud.append(asso_id['St'+str(study_id)])
                projects[study_projects]['studies'] = ','.join(p_stud)
                print "add to " + study_projects + "----> " + str(p_stud)
                print "###############################################################"
    
                dico={
                    'id' : asso_id['St'+str(study_id)],
                    'owner' : Dataset_owner,
                    'projects' : asso_id['PR'+str(project_id)],
                    'assays' : "",
                    'factors' : "",
                    'signatures' : "",
                    'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the human",
                    'description' : study_description,
                    'experimental_design' : "Human cryopreserved hepatocytes were purchased from Tissue Transformation Technologies, Inc. (Edison, NJ, USA) and CellzDirect, Inc. (Pittsboro, NC, USA). Six lots of human hepatocytes were used during the course of the project.",
                    'results' : "",
                    'study_type' : 'Interventional',
                    'last_update' : str(ztime),
                    'inclusion_period': "",
                    'inclusion': "",
                    'exclusion': "",
                    'status' : 'public',
                    'followup': "",
                    'population_size' : "",
                    'pubmed' : "",
                    'tags' : "",
                    'info' : "",
                    'warnings' : "",
                    'critical' : "",
                    'excel_id' : 'St'+str(study_id)
                }      
                
                studies['St'+str(study_id)]=dico
                
                #Create study excel
                title_line = 6 
                
                format = workbook.add_format()
                format.set_pattern(1)  # This is optional when using a solid fill.
                format.set_bg_color('green')

                study_worksheet.write('C1', '# Fill the study description')
                study_worksheet.write('C2', '# Each study is defined by one unique title (one by line) need to be associated with only one project')
                study_worksheet.write('C3', '# A study is the detail description of your experimentations')
                study_worksheet.write('C4', 'Only for observational studies',format)
                
                study_worksheet.write('A6', 'Study Id')
                study_worksheet.write('B6', 'Associated project')
                study_worksheet.write('C6', 'Study Title')
                study_worksheet.write('D6', 'Description')
                study_worksheet.write('E6', 'Design')
                study_worksheet.write('F6', 'Results')
                study_worksheet.write('G6', 'Study type ')
                study_worksheet.write('H6', 'Inclusion period')
                study_worksheet.write('I6', 'Inclusion criteria')
                study_worksheet.write('J6', 'Exclusion criteria')
                study_worksheet.write('K6', 'Follow up')
                study_worksheet.write('L6', 'Pubmed Id(s) (comma separated)')
                study_worksheet.write('M6', 'Interventional')
                
                study_worksheet.write('A'+str(title_line + study_id), 'St'+str(study_id))
                study_worksheet.write('B'+str(title_line + study_id), 'PR'+str(project_id))
                study_worksheet.write('C'+str(title_line + study_id), "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" in the human")
                study_worksheet.write('D'+str(title_line + study_id), study_description)
                study_worksheet.write('E'+str(title_line + study_id), str("Human cryopreserved hepatocytes were purchased from Tissue Transformation Technologies, Inc. (Edison, NJ, USA) and CellzDirect, Inc. (Pittsboro, NC, USA). Six lots of human hepatocytes were used during the course of the project.").decode('utf-8'))
                study_worksheet.write('F'+str(title_line + study_id), "")
                study_worksheet.write('G'+str(title_line + study_id), "")
                
                
                for cond in orga[project][studorg] :
                    assay_id += 1
                    dose = cond.split('+')[0]
                    print cond
                    temps = cond.split('+')[1]
                    print temps
                     #CREATION INFORMATION CONDITION

                     #RECUPERATION NOM | CAS | ROUTE DU CHEMICAL
                    condName = orga[project][studorg][cond]
                    info = dico_cond[condName]
                    prezfile = 1
                    if condName in dDataset :
                        upFile = open(projectPath+'Conditions/'+condName+'_up.txt','r')
                        downFile = open(projectPath+'Conditions/'+condName+'_down.txt','r')
                    else :
                        prezfile = 0

                    CAS = getFileCasHuman(condName)
                    dCas = getCAS()
                    if CAS.rstrip() not in dCas :
                        chemName = files.split('+')[2]+' CAS:NA'
                        chemID = ""
                    else :
                        chemName = dCas[CAS.rstrip()][0]
                        chemID = dCas[CAS.rstrip()][1]
                    chemRoute = ""
                    if condName in dCAS :
                        if dCAS[condName] in dRoute :
                            chemRoute = dRoute[dCAS[condName]]
                        else :
                            chemRoute = "other"
                    
    
                   
                    if chemID != "" :
                         chemtag = get_tag('chemical.tab',chemID)
                    else : 
                        chemtag =chemName
                  
                    doses = dose.split('_')[0]
                    dose_unit = dose.split('_')[1].replace('mgkg','mg/kg')
                    exposure = temps.split('_')[0]
                    exposure_unit = temps.split('_')[1]
                    timeexpo = 0
                    # CHANGE TIME UNIT
                    if exposure_unit == 'd' :
                        exposure_unit = "days"
                        timeexpo = float(exposure) * 1440
                    if exposure_unit == 'hr' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'h' :
                        exposure_unit = "hours"
                        timeexpo = float(exposure) * 60
                    if exposure_unit == 'min' :
                        exposure_unit = "minutes"
                        timeexpo = float(exposure) * 1
                        
                    #Excel id -> databas id
                    asso_id['As'+str(assay_id)] = 'TSA'+str(get_Index('assay'))
                    reverse_asso[asso_id['As'+str(assay_id)]] = 'As'+str(assay_id)
        
                    #Add assay id to associated study
                    s_assay = studies['St'+str(study_id)]['assays'].split()
                    s_assay.append(asso_id['As'+str(assay_id)])
                    studies['St'+str(study_id)]['assays'] = ','.join(s_assay)
        
                    #Add assay to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
                    print project_asso
        
                    p_assay = projects['PR'+str(project_id)]['assays'].split()
                    p_assay.append(asso_id['As'+str(assay_id)])
                    projects['PR'+str(project_id)]['assays'] = ','.join(p_assay)
        
                    #After reading line add all info in dico project
                    tag = get_tag('species.tab','NCBITaxon:9606')
                    tissue_tag = get_tag('tissue.tab',tissue_ID)
                    tag.extend(tissue_tag)
                    
                    dico={
                        'id' : asso_id['As'+str(assay_id)] ,
                        'studies' : asso_id['St'+str(study_id)],
                        'factors' : "",
                        'signatures' : "",
                        'projects' : studies['St'+str(study_id)]['projects'],
                        'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the human",
                        'organism' : 'Homo sapiens',
                        'experimental_type' : 'in vitro',
                        'developmental_stage' : '',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'tissue' : tissue_name,
                        'cell' : "Hepatocytes",
                        'status' : 'public',
                        'last_update' : str(ztime),
                        'cell_line' : "",
                        'additional_information' : "primary cell culture",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'As'+str(assay_id),
                        'pop_age' : "",
                        'location': "",
                        'reference' : "",
                        'matrice' : ""
                    }
                    assays['As'+str(assay_id)] = dico
                    
                    #Create study excel
                    title_line = 12 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    asssay_worksheet.write('A12', 'Assay Id')
                    asssay_worksheet.write('B12', 'Associated study')
                    asssay_worksheet.write('C12', 'Title')
                    asssay_worksheet.write('D12', 'Organism')
                    asssay_worksheet.write('E12', 'Developmental stage')
                    asssay_worksheet.write('F12', 'Generation')
                    asssay_worksheet.write('G12', 'Sex')
                    asssay_worksheet.write('H12', 'Tissue')
                    asssay_worksheet.write('I12', 'Cell')
                    asssay_worksheet.write('J12', 'Cell Line')
                    asssay_worksheet.write('K12', 'Experimental type')
                    asssay_worksheet.write('L12', 'Additional information')
                    asssay_worksheet.write('M12', 'Population age')
                    asssay_worksheet.write('N12', 'Geographical location')
                    asssay_worksheet.write('O12', 'Controle / Reference')
                    asssay_worksheet.write('P12', 'Biological matrice')
                    
                    asssay_worksheet.write('A'+str(title_line + assay_id), 'As'+str(assay_id))
                    asssay_worksheet.write('B'+str(title_line + assay_id), 'St'+str(study_id))
                    asssay_worksheet.write('C'+str(title_line + assay_id), "Open TG-GATEs  - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the human")
                    asssay_worksheet.write('D'+str(title_line + assay_id), 'NCBITaxon:9606')
                    asssay_worksheet.write('E'+str(title_line + assay_id), '')
                    asssay_worksheet.write('F'+str(title_line + assay_id), "f0")
                    asssay_worksheet.write('G'+str(title_line + assay_id), "Male")
                    asssay_worksheet.write('H'+str(title_line + assay_id), tissue_ID)
                    asssay_worksheet.write('K'+str(title_line + assay_id), 'in vitro')
                    asssay_worksheet.write('I'+str(title_line + assay_id), 'Hepatocytes')
                    asssay_worksheet.write('L'+str(title_line + assay_id), "primary cell culture")
                    
                    factor_id += 1
                                        
                    
                    #Excel id -> databas id
                    asso_id['Fc'+str(factor_id)] = 'TSF'+str(get_Index('factor'))
                    reverse_asso[asso_id['Fc'+str(factor_id)]] = 'Fc'+str(factor_id)
        
                    #Add factor id to associated assay
                    a_factor = assays['As'+str(assay_id)]['factors'].split()
                    a_factor.append(asso_id['Fc'+str(factor_id)])
                    assays['As'+str(assay_id)]['factors'] = ','.join(a_factor)
        
                    #Add factor to the associated study
                    study_asso = reverse_asso[assays['As'+str(assay_id)]['studies']]
        
                    s_factor = studies['St'+str(study_id)]['factors'].split()
                    s_factor.append(asso_id['Fc'+str(factor_id)])
                    studies['St'+str(study_id)]['factors'] = ','.join(s_factor)
        
                    #Add factor to the associated project
                    project_asso = assays['As'+str(assay_id)]['projects']
        
                    p_factor = projects['PR'+str(project_id)]['factors'].split()
                    p_factor.append(asso_id['Fc'+str(factor_id)])
                    projects['PR'+str(project_id)]['factors'] = ','.join(p_factor)

                    tag.extend(chemtag)
                    myset = list(set(tag))
                    tag = myset
        

        
                    #After reading line add all info in dico project
                    dico={
                        'id' : asso_id['Fc'+str(factor_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'studies' : assays['As'+str(assay_id)]['studies'],
                        'project' : assays['As'+str(assay_id)]['projects'],
                        'type' : "Chemical",
                        'chemical' : chemName,
                        'physical' : "",
                        'biological' : "",
                        'route' : chemRoute,
                        'last_update' : str(ztime),
                        'status' : 'public',
                        'vehicle' : 'NA',
                        'dose' : str(doses) +" "+ dose_unit,
                        'exposure_duration' : str(exposure) +" "+ exposure_unit,
                        'exposure_frequencies' : "",
                        'additional_information' : "For the in vitro studies, the highest concentration was defined as the dose level yielding an 80–90% relative survival ratio. However, for compounds that dissolved poorly in the vehicle, the highest concentration was defined by the maximum solubility of the compound. In principle, the ratio of the concentrations for the low, middle and high dose levels was 1:5:25.",
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Fc'+str(factor_id)
                    }
                    factors['Fc'+str(factor_id)] = dico


                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    factor_worksheet.write('A6', 'Factor Id')
                    factor_worksheet.write('B6', 'Associated assay')
                    factor_worksheet.write('C6', 'Exposition factor')
                    factor_worksheet.write('D6', 'Chemical name')
                    factor_worksheet.write('E6', 'Physical')
                    factor_worksheet.write('F6', 'Biological')
                    factor_worksheet.write('G6', 'Route')
                    factor_worksheet.write('H6', 'Vehicle')
                    factor_worksheet.write('I6', 'Dose')
                    factor_worksheet.write('J6', 'Dose unit')
                    factor_worksheet.write('K6', 'Exposure duration')
                    factor_worksheet.write('L6', 'Exposure duration unit')
                    factor_worksheet.write('M6', 'Exposure frequecies')
                    factor_worksheet.write('N6', 'Additional information')

                    
                    factor_worksheet.write('A'+str(title_line + factor_id), 'Fc'+str(factor_id))
                    factor_worksheet.write('B'+str(title_line + factor_id), 'As'+str(assay_id))
                    factor_worksheet.write('C'+str(title_line + factor_id), "Chemical")
                    factor_worksheet.write('D'+str(title_line + factor_id), chemName)
                    factor_worksheet.write('E'+str(title_line + factor_id), "")
                    factor_worksheet.write('F'+str(title_line + factor_id), "")
                    factor_worksheet.write('G'+str(title_line + factor_id), chemRoute)
                    factor_worksheet.write('H'+str(title_line + factor_id), 'NA')
                    factor_worksheet.write('I'+str(title_line + factor_id), str(doses))
                    factor_worksheet.write('J'+str(title_line + factor_id), dose_unit)
                    factor_worksheet.write('K'+str(title_line + factor_id), str(exposure))
                    factor_worksheet.write('L'+str(title_line + factor_id), exposure_unit)
                    factor_worksheet.write('M'+str(title_line + factor_id), '')
                    factor_worksheet.write('N'+str(title_line + factor_id), str("For the in vitro studies, the highest concentration was defined as the dose level yielding an 80–90% relative survival ratio. However, for compounds that dissolved poorly in the vehicle, the highest concentration was defined by the maximum solubility of the compound. In principle, the ratio of the concentrations for the low, middle and high dose levels was 1:5:25.").decode('utf-8'))
                    
                    
                    signature_id += 1
                    
                    #Excel id -> databas id
                    asso_id['Si'+str(signature_id)] = 'TSS'+str(get_Index('signature'))
                    reverse_asso[asso_id['Si'+str(signature_id)]] = 'Si'+str(signature_id)
        
                    #Add signature id to associated assay
                    a_signature = assays['As'+str(assay_id)]['signatures'].split()
        
                    a_signature.append(asso_id['Si'+str(signature_id)])
                    assays['As'+str(assay_id)]['signatures'] = ','.join(a_signature)
        
                    #Add factor to the associated study
        
                    s_signature = studies['St'+str(study_id)]['signatures'].split()
                    s_signature.append(asso_id['Si'+str(signature_id)])
                    studies['St'+str(study_id)]['signatures'] = ','.join(s_signature)
        
                    #Add factor to the associated project
                    project_asso = studies['St'+str(study_id)]['projects']
        
                    p_signature = projects['PR'+str(project_id)]['signatures'].split()
                    p_signature.append(asso_id['Si'+str(signature_id)])
                    projects['PR'+str(project_id)]['signatures'] = ','.join(p_signature)
        
                    #get factors
                    tag.extend(get_tag('experiment.tab','OBI:0400147'))
                    myset = list(set(tag))
                    tag = myset
                    
                    
                   
                   
                    dirCond = public_path+Dataset_ID+"/"+asso_id['Si'+str(signature_id)]
                    geneup = []
                    genedown = []
                    interofile =""
                    file_up = ""
                    file_down = ""
                
                    os.makedirs(dirCond)
                    if prezfile == 1:
                        upfile = condName+'_up.txt'
                        lId = []
                        for idline in upFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            geneup.append(idline.replace('\n',''))
                        lId = list(set(lId))
                        upFile.close()
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_up.txt')):
                            os.remove(os.path.join(dirCond,condName+'_up.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_up.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                
                        check_files.close()
                        
                        
                        
                        downfile = condName+'_down.txt'
                        lId = []
                        for idline in downFile.readlines():
                            IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                            lId.append(IDs.split('\t')[0])
                            genedown.append(idline.replace('\n',''))
                        downFile.close()
                        lId = list(set(lId))
                        dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                        lresult = {}
                        for i in dataset_in_db:
                            lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                        #Create 4 columns signature file
                        if os.path.isfile(os.path.join(dirCond,condName+'_down.txt')):
                            os.remove(os.path.join(dirCond,condName+'_down.txt'))
            
                        check_files = open(os.path.join(dirCond,condName+'_down.txt'),'a')
                        for ids in lId :
                            if ids in lresult :
                                check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                            else :
                                check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                  
                        check_files.close() 
               
            
                        
                        
                        
                    if os.path.isfile(os.path.join(dirCond,'genomic_interrogated_genes.txt')):
                        os.remove(os.path.join(dirCond,'genomic_interrogated_genes.txt'))
                    interofile = 'genomic_interrogated_genes.txt'
                    cmd3 = 'cp %s %s' % (projectPath+'all_genes_converted.txt',dirCond+'/genomic_interrogated_genes.txt')
                    os.system(cmd3)
                    
                    
                    
                    upload_path = admin_path
                    all_name = asso_id['Si'+str(signature_id)]+'.sign'
                    adm_path_signame = os.path.join(upload_path,'signatures_data',all_name)
                    #admin
                    if not os.path.exists(os.path.join(upload_path,'signatures_data')):
                        os.makedirs(os.path.join(upload_path,'signatures_data'))
                    if os.path.isfile(adm_path_signame):
                        os.remove(adm_path_signame)
                
                    check_files = open(adm_path_signame,'a')
                    lfiles = {'genomic_upward.txt':'1','genomic_downward.txt':'-1','genomic_interrogated_genes.txt':'0'}
                    val_geno = 0
                    for filesUsr in os.listdir(dirCond) :
                        if filesUsr in lfiles:
                            fileAdmin = open(dirCond +'/'+filesUsr,'r')
                            print dirCond +'/'+filesUsr
                            for linesFile in fileAdmin.readlines():
                                check_files.write(linesFile.replace('\n','')+'\t'+lfiles[filesUsr]+'\n')
                            fileAdmin.close()
                    check_files.close()
                    
        
                    dico ={
                        'id' : asso_id['Si'+str(signature_id)],
                        'studies' : asso_id['St'+str(study_id)],
                        'assays' : asso_id['As'+str(assay_id)],
                        'projects' : studies['St'+str(study_id)]['projects'] ,
                        'title' : "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the human",
                        'type' : 'Genomic',
                        'organism' : 'Homo sapiens',
                        'developmental_stage' : '',
                        'generation' : 'f0',
                        'sex' : 'Male',
                        'last_update' : str(ztime),
                        'tissue' : tissue_name,
                        'cell' : 'Hepatocytes',
                        'status' : 'public',
                        'cell_line' : "",
                        'molecule' : "",
                        'pathology' : "",
                        'technology' : 'Microarray',
                        'plateform' : 'GPL1355',
                        'observed_effect' : '',
                        'control_sample' : dSample[condName][0],
                        'treated_sample' : dSample[condName][1],
                        'pvalue' : '0.05',
                        'cutoff' : '1,5',
                        'study_type':'Interventional',
                        'statistical_processing' : 'Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.',
                        'additional_file' : "",
                        'file_up' : upfile,
                        'file_down' : downfile,
                        'file_interrogated' : interofile,
                        'genes_identifier': 'Entrez genes',
                        'tags' : ','.join(tag),
                        'owner' : Dataset_owner,
                        'info' : "",
                        'unexposed' : "",
                        'exposed' : "",
                        'significance_stat' : "",
                        'stat_value' : "",
                        'stat_adjustments' : "",
                        'stat_other' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'Si'+str(signature_id),
                        'genes_up' : ','.join(geneup),
                        'genes_down' : ','.join(genedown)
                    }
                    signatures['Si'+str(signature_id)] = dico
                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')
    
                    
                    signature_worksheet.write('A6', 'Signature Id')
                    signature_worksheet.write('B6', 'Associated study')
                    signature_worksheet.write('C6', 'Associated assay')
                    signature_worksheet.write('D6', 'Title')
                    signature_worksheet.write('E6', 'Signature type')
                    signature_worksheet.write('F6', 'Organism')
                    signature_worksheet.write('G6', 'Developmental stage')
                    signature_worksheet.write('H6', 'Generation')
                    signature_worksheet.write('I6', 'Sex')
                    signature_worksheet.write('J6', 'Tissue')
                    signature_worksheet.write('K6', 'Cell')
                    signature_worksheet.write('L6', 'Cell Line')
                    signature_worksheet.write('M6', 'Molecule')
                    signature_worksheet.write('N6', 'Associated phenotype, diseases processes or pathway / outcome')
                    signature_worksheet.write('O6', 'Technology used')
                    signature_worksheet.write('P6', 'Plateform')
                    signature_worksheet.write('Q6', 'controle / unexposed (n=)')
                    signature_worksheet.write('R6', 'case / exposed (n=)')
                    signature_worksheet.write('S6', 'Observed effect')
                    signature_worksheet.write('T6', 'Statistical significance')
                    signature_worksheet.write('U6', 'Satistical value')
                    signature_worksheet.write('V6', 'Statistical adjustments')
                    signature_worksheet.write('W6', 'Other satistical information')
                    signature_worksheet.write('X6', 'Control sample')
                    signature_worksheet.write('Y6', 'Treated sample')
                    signature_worksheet.write('Z6', 'pvalue')
                    signature_worksheet.write('AA6', 'Cutoff')
                    signature_worksheet.write('AB6', 'Statistical processing')
                    signature_worksheet.write('AC6', 'Additional file')
                    signature_worksheet.write('AD6', 'File up')
                    signature_worksheet.write('AE6', 'File down')
                    signature_worksheet.write('AF6', 'Interrogated genes file')
                    
                    signature_worksheet.write('A'+str(title_line + signature_id), 'Si'+str(signature_id))
                    signature_worksheet.write('B'+str(title_line + signature_id), 'St'+str(study_id))
                    signature_worksheet.write('C'+str(title_line + signature_id), 'As'+str(assay_id))
                    signature_worksheet.write('D'+str(title_line + signature_id), "Open TG-GATEs - Toxicogenomic signatures of "+tissue_name+" after exposure to "+project+" ("+doses+" "+dose_unit+", "+exposure+" "+exposure_unit+") in the human")
                    signature_worksheet.write('E'+str(title_line + signature_id), 'Genomic')
                    signature_worksheet.write('F'+str(title_line + signature_id), 'Homo sapiens')
                    signature_worksheet.write('G'+str(title_line + signature_id), "")
                    signature_worksheet.write('H'+str(title_line + signature_id), "f0")
                    signature_worksheet.write('I'+str(title_line + signature_id), "Male")
                    signature_worksheet.write('J'+str(title_line + signature_id), tissue_name)
                    signature_worksheet.write('K'+str(title_line + signature_id), "Hepatocytes")
                    signature_worksheet.write('L'+str(title_line + signature_id), "")
                    signature_worksheet.write('M'+str(title_line + signature_id), "")
                    signature_worksheet.write('N'+str(title_line + signature_id), "")
                    signature_worksheet.write('O'+str(title_line + signature_id), 'OBI:0400147')
                    signature_worksheet.write('P'+str(title_line + signature_id), 'GPL1355')
                    signature_worksheet.write('Q'+str(title_line + signature_id), "")
                    signature_worksheet.write('R'+str(title_line + signature_id), "")
                    signature_worksheet.write('S'+str(title_line + signature_id), "")
                    signature_worksheet.write('T'+str(title_line + signature_id), "")
                    signature_worksheet.write('U'+str(title_line + signature_id), "")
                    signature_worksheet.write('V'+str(title_line + signature_id), "")
                    signature_worksheet.write('W'+str(title_line + signature_id), "")
                    signature_worksheet.write('X'+str(title_line + signature_id), dSample[condName][0])
                    signature_worksheet.write('Y'+str(title_line + signature_id), dSample[condName][1])
                    signature_worksheet.write('Z'+str(title_line + signature_id), '0.05')
                    signature_worksheet.write('AA'+str(title_line + signature_id), '1.5')
                    signature_worksheet.write('AB'+str(title_line + signature_id), str('Affymetrix GeneChip data were quality controlled and normalized using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.').decode('utf-8'))
                    signature_worksheet.write('AC'+str(title_line + signature_id), "")
                    signature_worksheet.write('AD'+str(title_line + signature_id), upfile)
                    signature_worksheet.write('AE'+str(title_line + signature_id), downfile)
                    signature_worksheet.write('AF'+str(title_line + signature_id), interofile)
        workbook.close()

        for proj in projects :
            ID = projects[proj]['id']
            projects[proj]['edges']  = {}
            for stud in studies:
                projects[proj]['edges'][studies[stud]['id']] = studies[stud]['assays'].split()
            for ass in assays:
                projects[proj]['edges'][assays[ass]['id']] = assays[ass]['signatures'].split()

            projects[proj]['edges'] = json.dumps(projects[proj]['edges'])
            db['projects'].insert(projects[proj])
            del projects[proj]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+projects[proj]['id']+"\" } }\n"
            bulk_insert += json.dumps(projects[proj])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for stud in studies:
            db['studies'].insert(studies[stud])
            del studies[stud]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+studies[stud]['id']+"\" } }\n"
            bulk_insert += json.dumps(studies[stud])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for ass in assays:
            db['assays'].insert(assays[ass])
            del assays[ass]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assays[ass]['id']+"\" } }\n"
            bulk_insert += json.dumps(assays[ass])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)

        for fac in factors:
            db['factors'].insert(factors[fac])
            del factors[fac]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"factors\" , \"_id\" : \""+factors[fac]['id']+"\" } }\n"
            bulk_insert += json.dumps(factors[fac])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)


        for sign in signatures:
            db['signatures'].insert(signatures[sign])
            del signatures[sign]['_id']
            es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signatures[sign]['id']+"\" } }\n"
            bulk_insert += json.dumps(signatures[sign])+"\n"
            if bulk_insert:
                es.bulk(body=bulk_insert)












def otherHuman():
    """
        Insert signatures extrated from ChemPSY processing
        To insert informations please make sur that the following repository is correctlly filled :
            - all_genes_converted files
            - Conditions repository with all individuals conditions
            - Description.txt file
            - projectName.txt file 
            - Studies directory
        This function also required :
            - Individual sample file (Data/files/ChemPSySampleNumber.txt)
            - ChemPSy_MESH.tsv file (Data/files/ChemPSy_MESH.tsv)
    """
    logger.debug('insertHuman - Load dictionnaries')
    projectPath = human_path
    all = open(data_path+"/condInfo_Human_GSE.txt",'r')
    dicoGSE = {}
    for lines in all.readlines():
        cond = lines.split('\t')[0]
        GSE = cond.split('+')[0]
        if GSE not in dicoGSE :
            if GSE != "TGGATE":
                dicoGSE[GSE] = []
    condall = open(data_path+"/condInfo_Human_GSE.txt",'r')
    dicoInfoGSE = {}
    for linesInfo in condall.readlines():
        GSE = linesInfo.split('\t')[17]
        if GSE not in dicoInfoGSE :
            if GSE != "TGGATE":
                dicoInfoGSE[GSE] = linesInfo.split('\t')
    


    for projectName in dicoGSE :
        dChemical = dicoCAS()
        dDataset = {}
        dico_cond = NewcondDico()
        dRoute = NewdicoRoute(projectName)
        dCAS = dicoCAS()
        dSample=dicoSampleHuman()
        dName = {}
        nb_dataset = 0
        nb_study = 0
        nb_cond = 0
        orga = human_toxOrg(projectName)
        #DEFINITION DES CONDITIONS PAR CHEMICAL
        for files in os.listdir(projectPath+'Conditions'):
            name = files.replace('_down.txt','').replace('_up.txt','').replace('_noeffects.txt','')
            if projectName in name :
                if name not in dDataset :
                    dDataset[name] =[]




        logger.debug('InsertDM - Insert project')
        for project in orga :
            logger.info(project)
            #print project
            project_id = 0
            study_id = 0
            assay_id = 0
            factor_id = 0
            signature_id = 0
            projects = {}
            studies = {}
            assays = {}
            factors = {}
            signatures = {}
            asso_id = {}
            reverse_asso = {}
            
            
            
            project_id += 1
            
            Dataset_authors = dicoInfoGSE[projectName][20]
            Dataset_email = 'h-yamada@nibio.go.jp'
            Dataset_conditions = []
            Dataset_contributors=['TOXsIgN Team']
            Dataset_pubmed = [dicoInfoGSE[projectName][16]]
            Dataset_extlink = "http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=%s" % (dicoInfoGSE[projectName][17])
            Dataset_description = ""
            Dataset_owner = dicoInfoGSE[projectName][20]
            Dataset_status = "public"
            Dataset_ID = 'TSP' + str(get_Index('project'))
            Dataset_title = "Toxicogenomic signatures after exposure to "+project+" in the human"

            # DATASET CREATION
            dt = datetime.datetime.utcnow()
            ztime = mktime(dt.timetuple())
            dico={
                    'id' : Dataset_ID,
                    'title' : Dataset_title,
                    'description' : Dataset_description,
                    'pubmed' : ','.join(Dataset_pubmed),
                    'contributor' : ','.join(Dataset_contributors),
                    'assays' : "",
                    'cross_link':Dataset_extlink,
                    'studies' : "",
                    'factors' : "",
                    'signatures' :"",
                    'last_update' : str(ztime),
                    'submission_date' : str(ztime),
                    'status' : 'public' ,
                    'owner' : Dataset_owner,
                    'author' : Dataset_authors ,
                    'tags' : "",
                    'edges' : "",
                    'info' : "",
                    'warnings' : "",
                    'critical' : "",
                    'excel_id' : 'PR'+str(project_id)
                }
            
            #Add to dico
            print "########################    PROJECT    ########################"
            asso_id['PR'+str(project_id)] = Dataset_ID
            print asso_id['PR'+str(project_id)]
            reverse_asso[asso_id['PR'+str(project_id)]] = 'PR'+str(project_id)
            projects['PR'+str(project_id)] = dico
            print "###############################################################"
            
            
            nb_dataset = nb_dataset + 1
            
            
            #Create project excel
            title_line = 5 
            project_path = os.path.join(public_path,Dataset_ID)
            os.makedirs(project_path)



            workbook = xlsxwriter.Workbook(project_path+'/TOXsIgN_'+Dataset_ID+'.xlsx')
            project_worksheet = workbook.add_worksheet('Projects')
            study_worksheet = workbook.add_worksheet('Studies')
            asssay_worksheet = workbook.add_worksheet('Assays')
            factor_worksheet = workbook.add_worksheet('Factors')
            signature_worksheet = workbook.add_worksheet('Signatures')
            project_worksheet.write('A1', '# TOXsIgN - Excel template version 0.3')
            project_worksheet.write('C1', '# Fill the project description')
            project_worksheet.write('C2', '# Each project is defined by one unique title (one by line)')
            project_worksheet.write('C3', '# A project is the global description of your studies')
            project_worksheet.write('A5', 'Project Id')
            project_worksheet.write('B5', 'Title')
            project_worksheet.write('C5', 'Description')
            project_worksheet.write('D5', 'PubMed Id(s) (comma separated)')
            project_worksheet.write('E5', 'Contributors (comma separated)')
            project_worksheet.write('A'+str(title_line + project_id), 'PR'+str(project_id))
            project_worksheet.write('B'+str(title_line + project_id), Dataset_title)
            project_worksheet.write('C'+str(title_line + project_id), Dataset_description)
            project_worksheet.write('D'+str(title_line + project_id), ','.join(Dataset_pubmed))
            project_worksheet.write('E'+str(title_line + project_id), ','.join(Dataset_contributors))
            
            organeList = ['HEPATOCYTES','HK-2','ISHIKAWA_CELLS','JURKAT_CELLS','MCF-7']
            for studorg in organeList  :
                if studorg in orga[project]:
                    study_id += 1


                    study = studorg
                    #print study


                    tissue_name = ''
                    tissue_ID = ''
                    study_description = ''
                    if study == 'LIVER' :
                        tissue_name = 'Liver'
                        tissue_ID = 'FMA:7197'
                        cell_ID = ""
                        cell_name = ""
                        study_description = "Complete dataset for human liver."

                    if study == 'HEPATOCYTES' :
                        cell_name = 'Hepatocytes'
                        tissue_name='Liver'
                        tissue_ID = 'FMA:7197'
                        cell_ID = ""
                        study_description = "Complete dataset for human hepatocytes."

                    if study == 'ISHIKAWA_CELLS' :
                        cell_name = 'Ishikawa cell'
                        tissue_name = 'Uterus'
                        tissue_ID = 'FMA:17558'
                        cell_ID = 'BTO:0003575'
                        study_description = "Complete dataset for human ishikawa cells."

                    if study == 'HK-2' :
                        cell_name = 'HK-2 cell'
                        tissue_name = 'Kidney'
                        tissue_ID = 'FMA:7203'
                        cell_ID = 'BTO:0003041'
                        study_description = "Complete dataset for human HK-2 cells."

                    if study == 'JURKAT_CELLS' :
                        cell_name = 'JURKAT cell'
                        tissue_name = 'T lymphocyte'
                        tissue_ID = 'FMA:62870'
                        cell_ID = 'BTO:0000661'
                        study_description = "Complete dataset for human JURKAT cells."

                    if study == 'MCF-7' :
                        cell_name = 'MCF-7 cell'
                        tissue_name = 'Breast'
                        tissue_ID = 'FMA:9601'
                        cell_ID = 'BTO:0000093'
                        study_description = "Complete dataset for human MCF-7 cells."
                    


                    print "########################    Study    ########################"
                    study_projects = 'PR'+str(project_id)
                    #Excel id -> databas id
                    asso_id['St'+str(study_id)] = 'TSE' + str(get_Index('study'))
                    print asso_id['St'+str(study_id)]
                    reverse_asso[asso_id['St'+str(study_id)]] = study_id
        
                    #Add studies id to associated project
                    p_stud = projects[study_projects]['studies'].split()
                    p_stud.append(asso_id['St'+str(study_id)])
                    projects[study_projects]['studies'] = ','.join(p_stud)
                    print "add to " + study_projects + "----> " + str(p_stud)
                    print "###############################################################"
        
                    dico={
                        'id' : asso_id['St'+str(study_id)],
                        'owner' : Dataset_owner,
                        'projects' : asso_id['PR'+str(project_id)],
                        'assays' : "",
                        'factors' : "",
                        'signatures' : "",
                        'title' : "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" in the human",
                        'description' : study_description,
                        'experimental_design' : dicoInfoGSE[projectName][25],
                        'results' : "",
                        'study_type' : 'Interventional',
                        'last_update' : str(ztime),
                        'inclusion_period': "",
                        'inclusion': "",
                        'exclusion': "",
                        'status' : 'public',
                        'followup': "",
                        'population_size' : "",
                        'pubmed' : "",
                        'tags' : "",
                        'info' : "",
                        'warnings' : "",
                        'critical' : "",
                        'excel_id' : 'St'+str(study_id)
                    }      
                    
                    studies['St'+str(study_id)]=dico
                    
                    #Create study excel
                    title_line = 6 
                    
                    format = workbook.add_format()
                    format.set_pattern(1)  # This is optional when using a solid fill.
                    format.set_bg_color('green')

                    study_worksheet.write('C1', '# Fill the study description')
                    study_worksheet.write('C2', '# Each study is defined by one unique title (one by line) need to be associated with only one project')
                    study_worksheet.write('C3', '# A study is the detail description of your experimentations')
                    study_worksheet.write('C4', 'Only for observational studies',format)
                    
                    study_worksheet.write('A6', 'Study Id')
                    study_worksheet.write('B6', 'Associated project')
                    study_worksheet.write('C6', 'Study Title')
                    study_worksheet.write('D6', 'Description')
                    study_worksheet.write('E6', 'Design')
                    study_worksheet.write('F6', 'Results')
                    study_worksheet.write('G6', 'Study type ')
                    study_worksheet.write('H6', 'Inclusion period')
                    study_worksheet.write('I6', 'Inclusion criteria')
                    study_worksheet.write('J6', 'Exclusion criteria')
                    study_worksheet.write('K6', 'Follow up')
                    study_worksheet.write('L6', 'Pubmed Id(s) (comma separated)')
                    study_worksheet.write('M6', 'Interventional')
                    
                    study_worksheet.write('A'+str(title_line + study_id), 'St'+str(study_id))
                    study_worksheet.write('B'+str(title_line + study_id), 'PR'+str(project_id))
                    study_worksheet.write('C'+str(title_line + study_id), "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" in the human")
                    study_worksheet.write('D'+str(title_line + study_id), study_description)
                    study_worksheet.write('E'+str(title_line + study_id), dicoInfoGSE[projectName][25])
                    study_worksheet.write('F'+str(title_line + study_id), "")
                    study_worksheet.write('G'+str(title_line + study_id), "")
                    
                    
                    for cond in orga[project][studorg] :
                        assay_id += 1
                        dose = cond.split('+')[0]
                        print cond
                        temps = cond.split('+')[1]
                        print temps
                         #CREATION INFORMATION CONDITION

                         #RECUPERATION NOM | CAS | ROUTE DU CHEMICAL
                        condName = orga[project][studorg][cond]
                        info = dico_cond[condName]
                        prezfile = 1
                        sex = info[3]
                        if condName in dDataset :
                            upFile = open(projectPath+'Conditions/'+condName+'_up.txt','r')
                            downFile = open(projectPath+'Conditions/'+condName+'_down.txt','r')
                        else :
                            prezfile = 0

                        CAS = getFileCasHuman(condName)
                        dCas = getCAS()
                        if CAS.rstrip() not in dCas :
                            chemName = files.split('+')[2]+' CAS:NA'
                            chemID = ""
                        else :
                            chemName = dCas[CAS.rstrip()][0]
                            chemID = dCas[CAS.rstrip()][1]
                        chemRoute = ""
                        if condName in dCAS :
                            if dCAS[condName] in dRoute :
                                chemRoute = dRoute[dCAS[condName]]
                            else :
                                chemRoute = "other"
                        
        
                       
                        if chemID != "" :
                             chemtag = get_tag('chemical.tab',chemID)
                        else : 
                            chemtag =chemName

                        if dose =="NA" or dose=='High' or dose=="Low":
                            doses = 0
                            dose_unit = "NA"
                        else :
                            dose_unit = dose[-2:]
                            doses = dose.replace(dose_unit,"")
                      
                        exposure = temps.split('_')[0]
                        exposure_unit = temps.split('_')[1]
                        timeexpo = 0
                        # CHANGE TIME UNIT
                        if exposure_unit == 'd' :
                            exposure_unit = "days"
                            timeexpo = float(exposure) * 1440
                        if exposure_unit == 'hr' :
                            exposure_unit = "hours"
                            timeexpo = float(exposure) * 60
                        if exposure_unit == 'h' :
                            exposure_unit = "hours"
                            timeexpo = float(exposure) * 60
                        if exposure_unit == 'min' :
                            exposure_unit = "minutes"
                            timeexpo = float(exposure) * 1
                            
                        #Excel id -> databas id
                        asso_id['As'+str(assay_id)] = 'TSA'+str(get_Index('assay'))
                        reverse_asso[asso_id['As'+str(assay_id)]] = 'As'+str(assay_id)
            
                        #Add assay id to associated study
                        s_assay = studies['St'+str(study_id)]['assays'].split()
                        s_assay.append(asso_id['As'+str(assay_id)])
                        studies['St'+str(study_id)]['assays'] = ','.join(s_assay)
            
                        #Add assay to the associated project
                        project_asso = studies['St'+str(study_id)]['projects']
                        print project_asso
            
                        p_assay = projects['PR'+str(project_id)]['assays'].split()
                        p_assay.append(asso_id['As'+str(assay_id)])
                        projects['PR'+str(project_id)]['assays'] = ','.join(p_assay)
            
                        #After reading line add all info in dico project
                        tag = get_tag('species.tab','NCBITaxon:9606')
                        tissue_tag = get_tag('tissue.tab',tissue_ID)
                        tag.extend(tissue_tag)
                        
                        if cell_ID != "":
                            cell_tag = get_tag('cell_line.tab',cell_ID)
                            tag.extend(cell_tag)

                        
                        dico={
                            'id' : asso_id['As'+str(assay_id)] ,
                            'studies' : asso_id['St'+str(study_id)],
                            'factors' : "",
                            'signatures' : "",
                            'projects' : studies['St'+str(study_id)]['projects'],
                            'title' : "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" ("+str(doses)+" "+str(dose_unit)+", "+str(exposure)+" "+str(exposure_unit)+") in the human",
                            'organism' : 'Homo sapiens',
                            'experimental_type' : info[4],
                            'developmental_stage' : info[6],
                            'generation' : info[7],
                            'sex' : sex,
                            'tissue' : tissue_name,
                            'cell' : "",
                            'status' : 'public',
                            'last_update' : str(ztime),
                            'cell_line' : cell_name,
                            'additional_information' : "cell line",
                            'tags' : ','.join(tag),
                            'owner' : Dataset_owner,
                            'info' : "",
                            'warnings' : "",
                            'critical' : "",
                            'excel_id' : 'As'+str(assay_id),
                            'pop_age' : "",
                            'location': "",
                            'reference' : "",
                            'matrice' : ""
                        }
                        assays['As'+str(assay_id)] = dico
                        
                        #Create study excel
                        title_line = 12 
                        
                        format = workbook.add_format()
                        format.set_pattern(1)  # This is optional when using a solid fill.
                        format.set_bg_color('green')
        
                        
                        asssay_worksheet.write('A12', 'Assay Id')
                        asssay_worksheet.write('B12', 'Associated study')
                        asssay_worksheet.write('C12', 'Title')
                        asssay_worksheet.write('D12', 'Organism')
                        asssay_worksheet.write('E12', 'Developmental stage')
                        asssay_worksheet.write('F12', 'Generation')
                        asssay_worksheet.write('G12', 'Sex')
                        asssay_worksheet.write('H12', 'Tissue')
                        asssay_worksheet.write('I12', 'Cell')
                        asssay_worksheet.write('J12', 'Cell Line')
                        asssay_worksheet.write('K12', 'Experimental type')
                        asssay_worksheet.write('L12', 'Additional information')
                        asssay_worksheet.write('M12', 'Population age')
                        asssay_worksheet.write('N12', 'Geographical location')
                        asssay_worksheet.write('O12', 'Controle / Reference')
                        asssay_worksheet.write('P12', 'Biological matrice')
                        
                        asssay_worksheet.write('A'+str(title_line + assay_id), 'As'+str(assay_id))
                        asssay_worksheet.write('B'+str(title_line + assay_id), 'St'+str(study_id))
                        asssay_worksheet.write('C'+str(title_line + assay_id), "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" ("+str(doses)+" "+str(dose_unit)+", "+str(exposure)+" "+str(exposure_unit)+") in the human")
                        asssay_worksheet.write('D'+str(title_line + assay_id), 'NCBITaxon:9606')
                        asssay_worksheet.write('E'+str(title_line + assay_id), info[6])
                        asssay_worksheet.write('F'+str(title_line + assay_id), info[7])
                        asssay_worksheet.write('G'+str(title_line + assay_id), sex)
                        asssay_worksheet.write('H'+str(title_line + assay_id), tissue_ID)
                        asssay_worksheet.write('K'+str(title_line + assay_id), info[4])
                        asssay_worksheet.write('I'+str(title_line + assay_id), '')
                        asssay_worksheet.write('J'+str(title_line + assay_id), cell_name)
                        asssay_worksheet.write('L'+str(title_line + assay_id), "cell line")
                        
                        factor_id += 1
                                            
                        
                        #Excel id -> databas id
                        asso_id['Fc'+str(factor_id)] = 'TSF'+str(get_Index('factor'))
                        reverse_asso[asso_id['Fc'+str(factor_id)]] = 'Fc'+str(factor_id)
            
                        #Add factor id to associated assay
                        a_factor = assays['As'+str(assay_id)]['factors'].split()
                        a_factor.append(asso_id['Fc'+str(factor_id)])
                        assays['As'+str(assay_id)]['factors'] = ','.join(a_factor)
            
                        #Add factor to the associated study
                        study_asso = reverse_asso[assays['As'+str(assay_id)]['studies']]
            
                        s_factor = studies['St'+str(study_id)]['factors'].split()
                        s_factor.append(asso_id['Fc'+str(factor_id)])
                        studies['St'+str(study_id)]['factors'] = ','.join(s_factor)
            
                        #Add factor to the associated project
                        project_asso = assays['As'+str(assay_id)]['projects']
            
                        p_factor = projects['PR'+str(project_id)]['factors'].split()
                        p_factor.append(asso_id['Fc'+str(factor_id)])
                        projects['PR'+str(project_id)]['factors'] = ','.join(p_factor)

                        tag.extend(chemtag)
                        myset = list(set(tag))
                        tag = myset
            

            
                        #After reading line add all info in dico project
                        dico={
                            'id' : asso_id['Fc'+str(factor_id)],
                            'assays' : asso_id['As'+str(assay_id)],
                            'studies' : assays['As'+str(assay_id)]['studies'],
                            'project' : assays['As'+str(assay_id)]['projects'],
                            'type' : "Chemical",
                            'chemical' : chemName,
                            'physical' : "",
                            'biological' : "",
                            'route' : info[15],
                            'last_update' : str(ztime),
                            'status' : 'public',
                            'vehicle' : info[14],
                            'dose' : str(doses) +" "+ dose_unit,
                            'exposure_duration' : str(exposure) +" "+ exposure_unit,
                            'exposure_frequencies' : "",
                            'additional_information' : dicoInfoGSE[projectName][25],
                            'tags' : ','.join(tag),
                            'owner' : Dataset_owner,
                            'info' : "",
                            'warnings' : "",
                            'critical' : "",
                            'excel_id' : 'Fc'+str(factor_id)
                        }
                        factors['Fc'+str(factor_id)] = dico


                        
                        #Create study excel
                        title_line = 6 
                        
                        format = workbook.add_format()
                        format.set_pattern(1)  # This is optional when using a solid fill.
                        format.set_bg_color('green')
        
                        
                        factor_worksheet.write('A6', 'Factor Id')
                        factor_worksheet.write('B6', 'Associated assay')
                        factor_worksheet.write('C6', 'Exposition factor')
                        factor_worksheet.write('D6', 'Chemical name')
                        factor_worksheet.write('E6', 'Physical')
                        factor_worksheet.write('F6', 'Biological')
                        factor_worksheet.write('G6', 'Route')
                        factor_worksheet.write('H6', 'Vehicle')
                        factor_worksheet.write('I6', 'Dose')
                        factor_worksheet.write('J6', 'Dose unit')
                        factor_worksheet.write('K6', 'Exposure duration')
                        factor_worksheet.write('L6', 'Exposure duration unit')
                        factor_worksheet.write('M6', 'Exposure frequecies')
                        factor_worksheet.write('N6', 'Additional information')

                        
                        factor_worksheet.write('A'+str(title_line + factor_id), 'Fc'+str(factor_id))
                        factor_worksheet.write('B'+str(title_line + factor_id), 'As'+str(assay_id))
                        factor_worksheet.write('C'+str(title_line + factor_id), "Chemical")
                        factor_worksheet.write('D'+str(title_line + factor_id), info[14])
                        factor_worksheet.write('E'+str(title_line + factor_id), "")
                        factor_worksheet.write('F'+str(title_line + factor_id), "")
                        factor_worksheet.write('G'+str(title_line + factor_id), info[15])
                        factor_worksheet.write('H'+str(title_line + factor_id), 'NA')
                        factor_worksheet.write('I'+str(title_line + factor_id), str(doses))
                        factor_worksheet.write('J'+str(title_line + factor_id), dose_unit)
                        factor_worksheet.write('K'+str(title_line + factor_id), str(exposure))
                        factor_worksheet.write('L'+str(title_line + factor_id), exposure_unit)
                        factor_worksheet.write('M'+str(title_line + factor_id), '')
                        factor_worksheet.write('N'+str(title_line + factor_id), dicoInfoGSE[projectName][25])
                        
                        
                        signature_id += 1
                        
                        #Excel id -> databas id
                        asso_id['Si'+str(signature_id)] = 'TSS'+str(get_Index('signature'))
                        reverse_asso[asso_id['Si'+str(signature_id)]] = 'Si'+str(signature_id)
            
                        #Add signature id to associated assay
                        a_signature = assays['As'+str(assay_id)]['signatures'].split()
            
                        a_signature.append(asso_id['Si'+str(signature_id)])
                        assays['As'+str(assay_id)]['signatures'] = ','.join(a_signature)
            
                        #Add factor to the associated study
            
                        s_signature = studies['St'+str(study_id)]['signatures'].split()
                        s_signature.append(asso_id['Si'+str(signature_id)])
                        studies['St'+str(study_id)]['signatures'] = ','.join(s_signature)
            
                        #Add factor to the associated project
                        project_asso = studies['St'+str(study_id)]['projects']
            
                        p_signature = projects['PR'+str(project_id)]['signatures'].split()
                        p_signature.append(asso_id['Si'+str(signature_id)])
                        projects['PR'+str(project_id)]['signatures'] = ','.join(p_signature)
            
                        #get factors
                        tag.extend(get_tag('experiment.tab','OBI:0400147'))
                        myset = list(set(tag))
                        tag = myset
                        
                        
                       
                       
                        dirCond = public_path+Dataset_ID+"/"+asso_id['Si'+str(signature_id)]
                        geneup = []
                        genedown = []
                        interofile =""
                        file_up = ""
                        file_down = ""
                    
                        os.makedirs(dirCond)
                        if prezfile == 1:
                            upfile = condName+'_up.txt'
                            lId = []
                            for idline in upFile.readlines():
                                IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                                lId.append(IDs.split('\t')[0])
                                geneup.append(idline.replace('\n',''))
                            lId = list(set(lId))
                            upFile.close()
                            dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                            lresult = {}
                            for i in dataset_in_db:
                                lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                            #Create 4 columns signature file
                            if os.path.isfile(os.path.join(dirCond,condName+'_up.txt')):
                                os.remove(os.path.join(dirCond,condName+'_up.txt'))
                
                            check_files = open(os.path.join(dirCond,condName+'_up.txt'),'a')
                            for ids in lId :
                                if ids in lresult :
                                    check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                                else :
                                    check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                
                            check_files.close()
                            
                            
                            
                            downfile = condName+'_down.txt'
                            lId = []
                            for idline in downFile.readlines():
                                IDs = idline.replace('\n','\t').replace(',','\t').replace(';','\t')
                                lId.append(IDs.split('\t')[0])
                                genedown.append(idline.replace('\n',''))
                            downFile.close()
                            lId = list(set(lId))
                            dataset_in_db = list(db['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                            lresult = {}
                            for i in dataset_in_db:
                                lresult[i['GeneID']]=[i['Symbol'],i['HID']]
                            #Create 4 columns signature file
                            if os.path.isfile(os.path.join(dirCond,condName+'_down.txt')):
                                os.remove(os.path.join(dirCond,condName+'_down.txt'))
                
                            check_files = open(os.path.join(dirCond,condName+'_down.txt'),'a')
                            for ids in lId :
                                if ids in lresult :
                                    check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                                else :
                                    check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')                  
                            check_files.close() 
                   
                
                            
                            
                            
                        if os.path.isfile(os.path.join(dirCond,'genomic_interrogated_genes.txt')):
                            os.remove(os.path.join(dirCond,'genomic_interrogated_genes.txt'))
                        interofile = 'genomic_interrogated_genes.txt'
                        cmd3 = 'cp %s %s' % (projectPath+'all_genes_converted.txt',dirCond+'/genomic_interrogated_genes.txt')
                        os.system(cmd3)
                        
                        
                        
                        upload_path = admin_path
                        all_name = asso_id['Si'+str(signature_id)]+'.sign'
                        adm_path_signame = os.path.join(upload_path,'signatures_data',all_name)
                        #admin
                        if not os.path.exists(os.path.join(upload_path,'signatures_data')):
                            os.makedirs(os.path.join(upload_path,'signatures_data'))
                        if os.path.isfile(adm_path_signame):
                            os.remove(adm_path_signame)
                    
                        check_files = open(adm_path_signame,'a')
                        lfiles = {'genomic_upward.txt':'1','genomic_downward.txt':'-1','genomic_interrogated_genes.txt':'0'}
                        val_geno = 0
                        for filesUsr in os.listdir(dirCond) :
                            if filesUsr in lfiles:
                                fileAdmin = open(dirCond +'/'+filesUsr,'r')
                                print dirCond +'/'+filesUsr
                                for linesFile in fileAdmin.readlines():
                                    check_files.write(linesFile.replace('\n','')+'\t'+lfiles[filesUsr]+'\n')
                                fileAdmin.close()
                        check_files.close()
                        
            
                        dico ={
                            'id' : asso_id['Si'+str(signature_id)],
                            'studies' : asso_id['St'+str(study_id)],
                            'assays' : asso_id['As'+str(assay_id)],
                            'projects' : studies['St'+str(study_id)]['projects'] ,
                            'title' : "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" ("+str(doses)+" "+str(dose_unit)+", "+str(exposure)+" "+str(exposure_unit)+") in the human",
                            'type' : 'Genomic',
                            'organism' : 'Homo sapiens',
                            'developmental_stage' : info[6],
                            'generation' : info[7],
                            'sex' : info[3],
                            'last_update' : str(ztime),
                            'tissue' : tissue_name,
                            'cell' : "",
                            'status' : 'public',
                            'cell_line' : cell_name,
                            'molecule' : "",
                            'pathology' : "",
                            'technology' : 'Microarray',
                            'plateform' : 'GPL1355',
                            'observed_effect' : '',
                            'control_sample' : dSample[condName][0],
                            'treated_sample' : dSample[condName][1],
                            'pvalue' : '0.05',
                            'cutoff' : '1,5',
                            'study_type':'Interventional',
                            'statistical_processing' : 'Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.',
                            'additional_file' : "",
                            'file_up' : upfile,
                            'file_down' : downfile,
                            'file_interrogated' : interofile,
                            'genes_identifier': 'Entrez genes',
                            'tags' : ','.join(tag),
                            'owner' : Dataset_owner,
                            'info' : "",
                            'unexposed' : "",
                            'exposed' : "",
                            'significance_stat' : "",
                            'stat_value' : "",
                            'stat_adjustments' : "",
                            'stat_other' : "",
                            'warnings' : "",
                            'critical' : "",
                            'excel_id' : 'Si'+str(signature_id),
                            'genes_up' : ','.join(geneup),
                            'genes_down' : ','.join(genedown)
                        }
                        signatures['Si'+str(signature_id)] = dico
                        
                        #Create study excel
                        title_line = 6 
                        
                        format = workbook.add_format()
                        format.set_pattern(1)  # This is optional when using a solid fill.
                        format.set_bg_color('green')
        
                        
                        signature_worksheet.write('A6', 'Signature Id')
                        signature_worksheet.write('B6', 'Associated study')
                        signature_worksheet.write('C6', 'Associated assay')
                        signature_worksheet.write('D6', 'Title')
                        signature_worksheet.write('E6', 'Signature type')
                        signature_worksheet.write('F6', 'Organism')
                        signature_worksheet.write('G6', 'Developmental stage')
                        signature_worksheet.write('H6', 'Generation')
                        signature_worksheet.write('I6', 'Sex')
                        signature_worksheet.write('J6', 'Tissue')
                        signature_worksheet.write('K6', 'Cell')
                        signature_worksheet.write('L6', 'Cell Line')
                        signature_worksheet.write('M6', 'Molecule')
                        signature_worksheet.write('N6', 'Associated phenotype, diseases processes or pathway / outcome')
                        signature_worksheet.write('O6', 'Technology used')
                        signature_worksheet.write('P6', 'Plateform')
                        signature_worksheet.write('Q6', 'controle / unexposed (n=)')
                        signature_worksheet.write('R6', 'case / exposed (n=)')
                        signature_worksheet.write('S6', 'Observed effect')
                        signature_worksheet.write('T6', 'Statistical significance')
                        signature_worksheet.write('U6', 'Satistical value')
                        signature_worksheet.write('V6', 'Statistical adjustments')
                        signature_worksheet.write('W6', 'Other satistical information')
                        signature_worksheet.write('X6', 'Control sample')
                        signature_worksheet.write('Y6', 'Treated sample')
                        signature_worksheet.write('Z6', 'pvalue')
                        signature_worksheet.write('AA6', 'Cutoff')
                        signature_worksheet.write('AB6', 'Statistical processing')
                        signature_worksheet.write('AC6', 'Additional file')
                        signature_worksheet.write('AD6', 'File up')
                        signature_worksheet.write('AE6', 'File down')
                        signature_worksheet.write('AF6', 'Interrogated genes file')
                        
                        signature_worksheet.write('A'+str(title_line + signature_id), 'Si'+str(signature_id))
                        signature_worksheet.write('B'+str(title_line + signature_id), 'St'+str(study_id))
                        signature_worksheet.write('C'+str(title_line + signature_id), 'As'+str(assay_id))
                        signature_worksheet.write('D'+str(title_line + signature_id), "Toxicogenomic signatures of "+tissue_name+" "+cell_name+" after exposure to "+project+" ("+str(doses)+" "+str(dose_unit)+", "+str(exposure)+" "+str(exposure_unit)+") in the human")
                        signature_worksheet.write('E'+str(title_line + signature_id), 'Genomic')
                        signature_worksheet.write('F'+str(title_line + signature_id), 'Homo sapiens')
                        signature_worksheet.write('G'+str(title_line + signature_id), info[6])
                        signature_worksheet.write('H'+str(title_line + signature_id), info[7])
                        signature_worksheet.write('I'+str(title_line + signature_id), info[3])
                        signature_worksheet.write('J'+str(title_line + signature_id), tissue_name)
                        signature_worksheet.write('K'+str(title_line + signature_id), "Hepatocytes")
                        signature_worksheet.write('L'+str(title_line + signature_id), "")
                        signature_worksheet.write('M'+str(title_line + signature_id), "")
                        signature_worksheet.write('N'+str(title_line + signature_id), "")
                        signature_worksheet.write('O'+str(title_line + signature_id), 'OBI:0400147')
                        signature_worksheet.write('P'+str(title_line + signature_id), 'GPL1355')
                        signature_worksheet.write('Q'+str(title_line + signature_id), "")
                        signature_worksheet.write('R'+str(title_line + signature_id), "")
                        signature_worksheet.write('S'+str(title_line + signature_id), "")
                        signature_worksheet.write('T'+str(title_line + signature_id), "")
                        signature_worksheet.write('U'+str(title_line + signature_id), "")
                        signature_worksheet.write('V'+str(title_line + signature_id), "")
                        signature_worksheet.write('W'+str(title_line + signature_id), "")
                        signature_worksheet.write('X'+str(title_line + signature_id), dSample[condName][0])
                        signature_worksheet.write('Y'+str(title_line + signature_id), dSample[condName][1])
                        signature_worksheet.write('Z'+str(title_line + signature_id), '0.05')
                        signature_worksheet.write('AA'+str(title_line + signature_id), '1.5')
                        signature_worksheet.write('AB'+str(title_line + signature_id), 'Affymetrix GeneChip data were quality controlled and normalized using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.')
                        signature_worksheet.write('AC'+str(title_line + signature_id), "")
                        signature_worksheet.write('AD'+str(title_line + signature_id), upfile)
                        signature_worksheet.write('AE'+str(title_line + signature_id), downfile)
                        signature_worksheet.write('AF'+str(title_line + signature_id), interofile)
            workbook.close()

            for proj in projects :
                ID = projects[proj]['id']
                projects[proj]['edges']  = {}
                for stud in studies:
                    projects[proj]['edges'][studies[stud]['id']] = studies[stud]['assays'].split()
                for ass in assays:
                    projects[proj]['edges'][assays[ass]['id']] = assays[ass]['signatures'].split()

                projects[proj]['edges'] = json.dumps(projects[proj]['edges'])
                db['projects'].insert(projects[proj])
                del projects[proj]['_id']
                es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
                bulk_insert = ''
                bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+projects[proj]['id']+"\" } }\n"
                bulk_insert += json.dumps(projects[proj])+"\n"
                if bulk_insert:
                    es.bulk(body=bulk_insert)

            for stud in studies:
                db['studies'].insert(studies[stud])
                del studies[stud]['_id']
                es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
                bulk_insert = ''
                bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+studies[stud]['id']+"\" } }\n"
                bulk_insert += json.dumps(studies[stud])+"\n"
                if bulk_insert:
                    es.bulk(body=bulk_insert)

            for ass in assays:
                db['assays'].insert(assays[ass])
                del assays[ass]['_id']
                es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
                bulk_insert = ''
                bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assays[ass]['id']+"\" } }\n"
                bulk_insert += json.dumps(assays[ass])+"\n"
                if bulk_insert:
                    es.bulk(body=bulk_insert)

            for fac in factors:
                db['factors'].insert(factors[fac])
                del factors[fac]['_id']
                es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
                bulk_insert = ''
                bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"factors\" , \"_id\" : \""+factors[fac]['id']+"\" } }\n"
                bulk_insert += json.dumps(factors[fac])+"\n"
                if bulk_insert:
                    es.bulk(body=bulk_insert)


            for sign in signatures:
                db['signatures'].insert(signatures[sign])
                del signatures[sign]['_id']
                es = elasticsearch.Elasticsearch([config.get('app:main','elastic_host')])
                bulk_insert = ''
                bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signatures[sign]['id']+"\" } }\n"
                bulk_insert += json.dumps(signatures[sign])+"\n"
                if bulk_insert:
                    es.bulk(body=bulk_insert)

        
        
        
        
