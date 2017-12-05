# -*- coding: utf-8 -*-
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
import xlrd

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
projectPath = config.get('setup','other_path')
dicoUser = {
	"GSE9387" :"dix.david@epa.gov",
	"GSE10015":"tiffanyd@amgen.com",
	"GSE10093":"fremar5@web.de",
	"GSE10408":"dix.david@epa.gov",
	"GSE10409":"dix.david@epa.gov",
	"GSE10411":"dix.david@epa.gov",
	"GSE10412":"dix.david@epa.gov",
	"GSE11695":"gpage@uab.edu",
	"GSE14553":"carlson@ge.com",
	"GSE14554":"carlson@ge.com",
	"GSE30861":"lfxty@hotmail.com",
	"GSE31540":"anne.kienhuis@gmail.com",
	"GSE33248":"suzuki@nihs.go.jp",
	"GSE36243":"j.vandelft@maastrichtuniversity.nl",
	"GSE40117":"tatyana.yordanova.doktorova@vub.ac.be",
	"GSE44783":"michael.roemer@uni-tuebingen.de",
	"GSE48126":"a.vitins@maastrichtuniversity.nl",
	"GSE48990":"tatyana.yordanova.doktorova@vub.ac.be",
	"GSE51969":"a.vitins@maastrichtuniversity.nl",
	"GSE53082":"michael.roemer@uni-tuebingen.de",
	"GSE53634":"mirjam.schaap@rivm.nl",
	"GSE58225":"borlak.juergen@mh-hannover.de",
	"GSE72081":"linda.rieswijk@maastrichtuniversity.nl",
	"GSE72755":"carlosverjan@comunidad.unam.mx",
	"GSE74676":"christine.e.baer2.ctr@mail.mil"
}

except_files = ["GSE48990+HEPARG+2-amino-3-methylimidazo(4,5-f)quinoline+F0+0.003mM+72_h","GSE44783+LIVER+4,4'-diaminodiphenylmethane+F0+50mgkg+4_d","GSE14554+PRIMARY_HEPATOCYTE+tetrachlorodibenzodioxin+F0+1nM+48_h","GSE14554+PRIMARY_HEPATOCYTE+3,4,5,3',4'-pentachlorobiphenyl+F0+10pM+48_h","GSE14554+PRIMARY_HEPATOCYTE+3,4,5,3',4'-pentachlorobiphenyl+F0+1nM+48_h","GSE30861+LIVER+silica_particles_(70_nm)+F0+200mgkg+6_h"]

def save_excel(input_file,gse):


    #Create error list
    
    asso_id = {}
    reverse_asso = {}

    #Read excel file
    wb = xlrd.open_workbook(input_file,encoding_override="cp1251")
    #Read project
    sh = wb.sheet_by_index(0)
    projects={}
    critical = 0
    dt = datetime.datetime.utcnow()
    ztime = mktime(dt.timetuple())
    user = dicoUser[gse]

    for rownum in range(5, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                continue
            project_error = {'Critical':[],'Warning':[],'Info':[]}

            project_id = row_values[0]
            project_title = ""
            project_description = ""
            project_pubmed = ""
            project_contributors=""
            project_crosslink = ""

            if row_values[1] != "":
                project_title = row_values[1]
            else :
                project_error['Critical'].append("No project title ("+project_id+")")
                critical += 1

            if row_values[2] != "":
                project_description = row_values[2]
            else :
                project_error['Warning'].append("No project description ("+project_id+")")

            if row_values[3] != "" :
                if ';' in str(row_values[3]) or '|' in str(row_values[3]):
                    project_error['Critical'].append("Use comma to separate your pubmed ids ("+project_id+")")
                    critical += 1
                else :
                    project_pubmed = str(row_values[3])
            else :
                project_error['Info'].append("No associated pubmed Id(s)")

            if row_values[4] != "" :
                if ';' in row_values[4] or '|' in row_values[4]:
                    project_error['Critical'].append("Use comma to separate your contributors ("+project_id+")")
                    critical += 1
                else :
                    project_contributors = row_values[4]
            else :
                project_error['Info'].append("No associated contributors ("+project_id+")")

            if row_values[5] != "" :
                if ';' in row_values[5] or '|' in row_values[5]:
                    project_error['Critical'].append("Use comma to separate your links ("+project_id+")")
                    critical += 1
                else :
                    project_crosslink = row_values[5]
            else :
                project_error['Info'].append("No cross link(s) ("+project_id+")")


            #After reading line add all info in dico project
            db['project'].update({'id': 1}, {'$inc': {'val': 1}})
            repos = db['project'].find({'id': 1})
            id_p = ""
            for res in repos:
                id_p = res

            #Excel id -> databas id
            asso_id[project_id] = 'TSP'+str(id_p['val'])
            reverse_asso[asso_id[project_id]] = project_id

            dico={
                'id' : asso_id[project_id],
                'title' : project_title,
                'description' : project_description,
                'pubmed' : project_pubmed,
                'contributor' : project_contributors,
                'assays' : "",
                'cross_link' : project_crosslink,
                'studies' : "",
                'factors' : "",
                'signatures' :"",
                'last_update' : str(ztime),
                'submission_date' : str(ztime),
                'status' : 'public' ,
                'owner' : user,
                'author' : user ,
                'tags' : "",
                'edges' : "",
                'info' : ','.join(project_error['Info']),
                'warnings' : ','.join(project_error['Warning']),
                'critical' : ','.join(project_error['Critical']),
                'excel_id' : project_id
            }
            projects[project_id] = dico

    # Check studies
    sh = wb.sheet_by_index(1)
    studies={}
    for rownum in range(6, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                continue
            study_error = {'Critical':[],'Warning':[],'Info':[]}

            study_id = row_values[0]
            study_projects = ""
            study_title = ""
            study_description=""
            study_experimental_design=""
            study_results=""
            study_type = ""
            study_inclusion_periode = ""
            study_inclusion = ""
            study_exclusion = ""
            study_followup = ""
            study_pubmed = ""
            study_pop_size = ""
            study_pubmed = ""

            if row_values[1] != "":
                if row_values[1] in projects:
                    study_projects = row_values[1]
                else :
                    study_error['Critical'].append("Project doesn't exists ("+study_id+")")
                    critical += 1
            else :
                study_error['Critical'].append("No associated project ("+study_id+")")
                critical += 1

            if row_values[2] != "":
                study_title = row_values[2]
            else :
                study_error['Critical'].append("No study title ("+study_id+")")
                critical += 1

            if row_values[3] != "":
                study_description = row_values[3]
            else :
                study_error['Warning'].append("No study description ("+study_id+")")

            if row_values[4] != "":
                study_experimental_design = row_values[4]
            else :
                study_error['Warning'].append("No experimental design description ("+study_id+")")

            if row_values[5] != "":
                study_results = row_values[5]
            else :
                study_error['Info'].append("No study results ("+study_id+")")

            if row_values[6] != "":
                if row_values[6] == 'Interventional' or row_values[6] == 'Observational' :
                    study_type = row_values[6]
                else :
                    study_error['Critical'].append("Study type not available ("+study_id+")")
                    critical += 1
            else :
                study_error['Critical'].append("No study type selected ("+study_id+")")
                critical += 1

            if study_type == "Observational" :
                if row_values[7] != "":
                    study_inclusion_periode = row_values[7]
                else :
                    study_error['Warning'].append("No inclusion period ("+study_id+")")

                if row_values[8] != "":
                    study_inclusion = row_values[8]
                else :
                    study_error['Warning'].append("No inclusion criteria ("+study_id+")")

                if row_values[9] != "":
                    study_exclusion = row_values[9]
                else :
                    study_error['Warning'].append("No exclusion criteria ("+study_id+")")

                if row_values[10] != "":
                    study_followup = row_values[10]
                else :
                    study_error['Warning'].append("No follow up ("+study_id+")")

                if row_values[11] != "":
                    study_pop_size = row_values[11]
                else :
                    study_error['Warning'].append("No population size ("+study_id+")")

                if row_values[12] != "":
                    study_pubmed = row_values[12]
                else :
                    study_error['Info'].append("No pubmed ("+study_id+")")


            #After reading line add all info in dico project
            db['study'].update({'id': 1}, {'$inc': {'val': 1}})
            repos = db['study'].find({'id': 1})
            id_s = ""
            for res in repos:
                id_s = res
            
            #Excel id -> databas id
            asso_id[study_id] = 'TSE'+str(id_s['val'])
            reverse_asso[asso_id[study_id]] = study_id

            #Add studies id to associated project
            p_stud = projects[study_projects]['studies'].split()
            p_stud.append(asso_id[study_id])
            projects[study_projects]['studies'] = ','.join(p_stud)

            dico={
                'id' : asso_id[study_id],
                'owner' : user,
                'projects' : asso_id[study_projects],
                'assays' : "",
                'factors' : "",
                'signatures' : "",
                'title' : study_title,
                'description' : study_description,
                'experimental_design' : study_experimental_design,
                'results' : study_results,
                'study_type' : study_type,
                'last_update' : str(ztime),
                'inclusion_period': study_inclusion_periode,
                'inclusion': study_inclusion,
                'status' : 'public',
                'followup': study_followup,
                'exclusion' : study_exclusion,
                'pop_size' : study_pop_size,
                'pubmed' : study_pubmed,
                'tags' : "",
                'info' : ','.join(study_error['Info']),
                'warnings' : ','.join(study_error['Warning']),
                'critical' : ','.join(study_error['Critical']),
                'excel_id' : study_id
            }      
            studies[study_id]=dico

    # List of TOXsIgN 'ontologies'
    list_developmental_stage = ['Fetal','Embryonic','Larva','Neo-Natal','Juvenile','Pre-pubertal','Pubertal','Adulthood','Elderly','NA']
    list_generation = ['f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','f10']
    list_experimental = ['in vivo','ex vivo','in vitro','other','NA']
    list_sex = ['Male','Female','Both','Other','NA']
    list_dose_unit = ['M','mM','µM','g/mL','mg/mL','µg/mL','ng/mL','mg/kg','µg/kg','µg/kg','ng/kg','%']
    list_exposure_duration_unit = ['week','day','hour','minute','seconde']
    list_exposition_factor = ['Chemical','Physical','Biological']
    list_signature_type = ['Physiological','Genomic','Molecular']
    list_observed_effect = ['Decrease','Increase','No effect','NA']
    

    # Check assay
    sh = wb.sheet_by_index(2)
    assays={}
    for rownum in range(12, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                continue
            assay_error = {'Critical':[],'Warning':[],'Info':[]}

            assay_id = row_values[0]
            assay_study = ""
            assay_title = ""
            assay_organism = ""
            assay_organism_name = ""
            assay_experimental_type = ""
            assay_developmental_stage = "" 
            assay_generation = ""
            assay_sex = ""
            assay_tissue = ""
            assay_tissue_name = ""
            assay_cell = ""
            assay_cell_name = ""
            assay_cell_line = ""
            assay_cell_line_name = ""   
            assay_additional_information = "" 
            tag = [] 
            assay_pop_age = ""
            assay_location = ""
            assay_reference = ""
            assay_matrice = "" 


            if row_values[1] != "":
                if row_values[1] in studies:
                    assay_study = row_values[1]
                else :
                    assay_error['Critical'].append("Studies doesn't exists ("+assay_id+")")
                    critical += 1
            else :
                study_error['Critical'].append("No associated study ("+assay_id+")")
                critical += 1

            if row_values[2] != "":
                assay_title = row_values[2]
            else :
                assay_error['Critical'].append("No study title ("+assay_id+")")
                critical += 1

            if row_values[4] != "":
                data = db['species.tab'].find_one({'id': row_values[4]})
                if data is None :
                    if row_values[3] == "" :
                        assay_organism = ""
                        assay_error['Critical'].append("Please select an organism in the TOXsIgN ontologies list ("+assay_id+")")
                        critical += 1
                    else :
                        assay_organism_name = row_values[3]
                        tag.append(row_values[3])
                else :
                    assay_organism = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[3] != "" :
                        assay_organism_name = row_values[3]
                        tag.append(row_values[3])
            else :
                assay_error['Critical'].append("No organism selected ("+assay_id+")")
                critical += 1

            if row_values[5] != "":
                if row_values[5] in  list_developmental_stage :
                    assay_developmental_stage = row_values[5]
                else :
                    assay_error['Warning'].append("Developmental stage not listed ("+assay_id+")")
            else :
                assay_error['Info'].append("No developmental stage selected ("+assay_id+")")
                

            if row_values[6] != "":
                if row_values[6] in  list_generation :
                    assay_generation = row_values[6]
                else :
                    assay_error['Warning'].append("Generation not listed ("+assay_id+")")
            else :
                assay_error['Info'].append("No generation selected ("+assay_id+")")

            if row_values[7] != "":
                if row_values[7] in  list_sex :
                    assay_sex = row_values[7]
                else :
                    assay_error['Warning'].append("Sex not listed ("+assay_id+")")
            else :
                assay_error['Info'].append("No sex selected ("+assay_id+")")

            if row_values[9] != "":
                data = db['tissue.tab'].find_one({'id': row_values[9]})
                if data is None :
                    if row_values[8] != "":
                        assay_tissue_name = row_values[8]
                        tag.append(assay_tissue_name)
                    else :
                        assay_tissue = ""
                        assay_error['Warning'].append("Please select a tissue in the TOXsIgN ontologies list ("+assay_id+")")
                else :
                    assay_tissue = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[8] != "":
                        assay_tissue_name = row_values[8]
                        tag.append(assay_tissue_name)

            if row_values[11] != "":
                data = db['cell.tab'].find_one({'id': row_values[11]})
                if data is None :
                    if row_values[10] != "":
                        assay_cell_name = row_values[10]
                        tag.append(assay_cell_name)
                    else :
                        assay_cell = ""
                        assay_error['Warning'].append("Please select a cell in the TOXsIgN ontologies list ("+assay_id+")")
                else :
                    assay_cell = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[10] != "":
                        assay_cell_name = row_values[10]
                        tag.append(assay_cell_name)



            if row_values[13] != "":
                data = db['cell_line.tab'].find_one({'id': row_values[13]})
                if data is None :
                    if row_values[12] != "":
                        assay_cell_line_name = row_values[12]
                        tag.append(assay_cell_line_name)
                    else :
                        assay_cell_line = ""
                        assay_error['Warning'].append("Please select a cell line in the TOXsIgN ontologies list ("+assay_id+")")
                else :
                    assay_cell_line = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[12] != "":
                        assay_cell_line_name = row_values[12]
                        tag.append(assay_cell_line_name)

            # Check if at least tissue/cell or cell line are filled
            if assay_cell_line == "" and assay_cell == "" and assay_tissue =="" :
                if studies[assay_study]['study_type'] !='Observational' :
                    assay_error['Critical'].append("Please select at least a tissue, cell or cell line in the TOXsIgN ontologies list ("+assay_id+")")
                    critical += 1

            if row_values[14] != "":
                if row_values[14] in  list_experimental :
                    assay_experimental_type = row_values[14]


            if studies[assay_study]['study_type'] =='Observational' :
                if row_values[15] != "":
                    assay_pop_age = row_values[15]
                else :
                    assay_error['Info'].append("No population age ("+assay_id+")")

                if row_values[16] != "":
                    assay_location = row_values[16]
                else :
                    assay_error['Info'].append("No geographical location ("+assay_id+")")

                if row_values[17] != "":
                    assay_reference = row_values[17]
                else :
                    assay_error['Info'].append("No controle / reference ("+assay_id+")")

                if row_values[18] != "":
                    assay_matrice = row_values[18]
                else :
                    assay_error['Info'].append("No matrice("+assay_id+")")

            if row_values[19] != "":
                assay_additional_information = row_values[19]

            #After reading line add all info in dico project
            db['assay'].update({'id': 1}, {'$inc': {'val': 1}})
            repos = db['assay'].find({'id': 1})
            id_a = ""
            for res in repos:
                id_a = res
            
            #Excel id -> databas id
            asso_id[assay_id] = 'TSA'+str(id_a['val'])
            reverse_asso[asso_id[assay_id]] = assay_id

            #Add assay id to associated study
            s_assay = studies[assay_study]['assays'].split()
            s_assay.append(asso_id[assay_id])
            studies[assay_study]['assays'] = ','.join(s_assay)

            #Add assay to the associated project
            project_asso = reverse_asso[studies[assay_study]['projects']]

            p_assay = projects[project_asso]['assays'].split()
            p_assay.append(asso_id[assay_id])
            projects[project_asso]['assays'] = ','.join(p_assay)

            #After reading line add all info in dico project
            dico={
                'id' : asso_id[assay_id] ,
                'studies' : asso_id[assay_study],
                'factors' : "",
                'signatures' : "",
                'projects' : studies[assay_study]['projects'],
                'title' : assay_title,
                'organism' : assay_organism,
                'organism_name' : assay_organism_name,
                'experimental_type' : assay_experimental_type,
                'developmental_stage' : assay_developmental_stage,
                'generation' : assay_generation,
                'sex' : assay_sex,
                'tissue' : assay_tissue,
                'tissue_name' : assay_tissue_name,
                'cell' : assay_cell,
                'cell_name' : assay_cell_name,
                'status' : 'public',
                'last_update' : str(ztime),
                'cell_line' : assay_cell_line,
                'cell_line_name' : assay_cell_line_name,
                'additional_information' : assay_additional_information,
                'population_age' : assay_pop_age,
                'geographical_location':assay_location,
                'reference':assay_reference,
                'matrice':assay_matrice,
                'tags' : ','.join(tag),
                'owner' : user,
                'info' : ','.join(assay_error['Info']),
                'warnings' : ','.join(assay_error['Warning']),
                'critical' : ','.join(assay_error['Critical']),
                'excel_id' : assay_id
            }
            assays[assay_id] = dico

    # Check factor
    sh = wb.sheet_by_index(3)
    factors={}
    for rownum in range(5, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" and row_values [4] =="" and row_values [5] =="" :
                continue

            factor_error = {'Critical':[],'Warning':[],'Info':[]}
    
            factor_id = row_values[0]
            factor_type = ""
            factor_assay = ""
            factor_chemical = ""
            factor_chemical_name = ""
            factor_physical = ""
            factor_biological = ""
            factor_route = ""
            factor_vehicle  = ""
            factor_dose = ""
            factor_dose_unit = ""
            factor_exposure_duration = ""
            factor_exposure_duration_unit = ""
            factor_exposure_frequecies = ""
            factor_additional_information = ""
            tag = []



            if row_values[1] != "":
                if row_values[1] in assays:
                    factor_assay = row_values[1]
                else :
                    factor_error['Critical'].append("Assay doesn't exists ("+factor_id+")")
                    critical += 1
            else :
                factor_error['Critical'].append("No associated study ("+factor_id+")")
                critical += 1

            if row_values[2] != "":
                if row_values[2] in  list_exposition_factor :
                    factor_type = row_values[2]
                else :
                    factor_error['Critical'].append("Exposition factor not listed ("+factor_id+")")
                    critical += 1
            else :
                factor_error['Critical'].append("No exposition factor selected ("+factor_id+")")
                critical += 1

            if row_values[3] != "":
                factor_chemical_name = row_values[3]

            if row_values[4] != "":
                data = db['chemical.tab'].find_one({'id': row_values[4]})
                if data is None :
                    if row_values[3] != "":
                        factor_chemical_name = row_values[3]
                        tag.append(factor_chemical_name)
                    else :
                        factor_chemical = ""
                        factor_error['Warning'].append("Chemical not in the TOXsIgN ontologies list ("+factor_id+")")
                else :
                    factor_chemical = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[3] != "":
                        factor_chemical_name = row_values[3]
                        tag.append(factor_chemical_name)      
            else :
                assay_error['Warning'].append("No chemical selected ("+factor_id+")")

            if row_values[5] != "":
                data = db['chemical.tab'].find_one({'id': row_values[5]})
                if data is None :
                    data =  'false'
                else :
                    data = 'true'
                if data == 'true' :
                    factor_physical = row_values[5]
                else :
                    a =1
                    #factor_error['Warning'].append("Physical factor not in the TOXsIgN ontologies (not available yet) ("+factor_id+")")
            else :
                a =1
                #factor_error['Warning'].append("No physical factor selected (not available yet) ("+factor_id+")")

            if row_values[6] != "":
                data = db['chemical.tab'].find_one({'id': row_values[6]})
                if data is None :
                    data =  'false'
                else :
                    data = 'true'
                if data == 'true' :
                    factor_biological = row_values[6]
                else :
                    a=1
                    f#actor_error['Warning'].append("Biological factor notin the TOXsIgN ontologies (not available yet) ("+factor_id+")")
            else :
                a=1
                #factor_error['Warning'].append("No biological factor selected (not available yet) ("+factor_id+")")

            if row_values[7] != "":
                factor_route = row_values[7]
            else :
                factor_error['Info'].append("No route ("+factor_id+")")

            if row_values[8] != "":
                factor_vehicle = row_values[8]
            else :
                factor_error['Info'].append("No vehicle ("+factor_id+")")

            if row_values[9] != "":
                factor_dose = str(row_values[9])
            else :
                factor_error['Critical'].append("Factor dose required ("+factor_id+")")
                critical += 1
            try :
                if row_values[10] != "":
                    if str(row_values[10]) in list_dose_unit :
                        factor_dose_unit = str(row_values[10])
                    else :
                        factor_dose_unit = row_values[10]
            except:
                factor_dose_unit = row_values[10]

            if row_values[11] != "":
                factor_exposure_duration = str(row_values[11])
            else :
                factor_error['Critical'].append("Factor exposure duration required ("+factor_id+")")
                critical += 1

            if row_values[12] != "":
                if row_values[12] in list_exposure_duration_unit :
                    factor_exposure_duration_unit = row_values[12]
                else :
                    factor_exposure_duration_unit = row_values[12]

            if row_values[13] != "":
                factor_exposure_frequecies = row_values[13]

            if row_values[14] != "":
                factor_additional_information = row_values[14]
    


            #After reading line add all info in dico project
            db['factor'].update({'id': 1}, {'$inc': {'val': 1}})
            repos = db['factor'].find({'id': 1})
            id_a = ""
            for res in repos:
                id_f = res
            
            #Excel id -> databas id
            asso_id[factor_id] = 'TSF'+str(id_f['val'])
            reverse_asso[asso_id[factor_id]] = factor_id

            #Add factor id to associated assay
            a_factor = assays[factor_assay]['factors'].split()
            a_factor.append(asso_id[factor_id])
            assays[factor_assay]['factors'] = ','.join(a_factor)

            #Add factor to the associated study
            study_asso = reverse_asso[assays[factor_assay]['studies']]

            s_factor = studies[study_asso]['factors'].split()
            s_factor.append(asso_id[factor_id])
            studies[study_asso]['factors'] = ','.join(s_factor)

            #Add factor to the associated project
            project_asso = reverse_asso[assays[factor_assay]['projects']]

            p_factor = projects[project_asso]['factors'].split()
            p_factor.append(asso_id[factor_id])
            projects[project_asso]['factors'] = ','.join(p_factor)

            #up factor tags to associated assy 
            tag_assay = assays[factor_assay]['tags'].split(',')
            tag_assay.extend(tag)
            assays[factor_assay]['tags'] = ','.join(tag_assay)

            #After reading line add all info in dico project
            try :
                dico={
                    'id' : asso_id[factor_id],
                    'assays' : asso_id[factor_assay],
                    'studies' : assays[factor_assay]['studies'],
                    'project' : assays[factor_assay]['projects'],
                    'type' : factor_type,
                    'chemical' : factor_chemical,
                    'chemical_name' : factor_chemical_name,
                    'physical' : factor_physical,
                    'biological' : factor_biological,
                    'route' : factor_route,
                    'last_update' : str(ztime),
                    'status' : 'public',
                    'vehicle' : factor_vehicle,
                    'dose' : str(factor_dose) +" "+ factor_dose_unit,
                    'exposure_duration' : str(factor_exposure_duration) +" "+ factor_exposure_duration_unit,
                    'exposure_frequencies' : factor_exposure_frequecies,
                    'additional_information' : factor_additional_information,
                    'tags' : ','.join(tag),
                    'owner' : user,
                    'info' : ','.join(factor_error['Info']),
                    'warnings' : ','.join(factor_error['Warning']),
                    'critical' : ','.join(factor_error['Critical']),
                    'excel_id' : factor_id
                }
            except :
                dico={
                    'id' : asso_id[factor_id],
                    'assays' : asso_id[factor_assay],
                    'studies' : assays[factor_assay]['studies'],
                    'project' : assays[factor_assay]['projects'],
                    'type' : factor_type,
                    'chemical' : factor_chemical,
                    'chemical_name' : factor_chemical_name,
                    'physical' : factor_physical,
                    'biological' : factor_biological,
                    'route' : factor_route,
                    'last_update' : str(ztime),
                    'status' : 'public',
                    'vehicle' : factor_vehicle,
                    'dose' : factor_dose +" "+ factor_dose_unit,
                    'exposure_duration' : factor_exposure_duration +" "+ factor_exposure_duration_unit,
                    'exposure_frequencies' : factor_exposure_frequecies,
                    'additional_information' : factor_additional_information,
                    'tags' : ','.join(tag),
                    'owner' : user,
                    'info' : ','.join(factor_error['Info']),
                    'warnings' : ','.join(factor_error['Warning']),
                    'critical' : ','.join(factor_error['Critical']),
                    'excel_id' : factor_id
                }
            factors[factor_id] = dico


    # Check signatures
    sh = wb.sheet_by_index(4)
    signatures={}
    for rownum in range(6, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" and row_values [4] =="" and row_values [5] =="" :
                continue

            signature_error = {'Critical':[],'Warning':[],'Info':[]}

            signature_id = row_values[0]
            signature_associated_study = ""
            signature_associated_assay = ""
            signature_title = ""
            signature_type = ""
            signature_organism = ""
            signature_organism_name = ""
            signature_developmental_stage = ""
            signature_generation = ""
            signature_sex = ""
            signature_tissue = ""
            signature_tissue_name = ""
            signature_cell = ""
            signature_cell_name = "" 
            signature_cell_line = ""
            signature_cell_line_name = ""
            signature_molecule = ""
            signature_molecule_name = ""
            signature_pathology = ""
            signature_technology = ""
            signature_technology_name = ""
            signature_plateform = ""
            signature_observed_effect = ""
            signature_control_sample = ""
            signature_treated_sample = ""
            signature_pvalue = ""
            signature_cutoff = "" 
            signature_satistical_processing = ""
            signature_additional_file = ""
            signature_file_up = "" 
            signature_file_down = ""
            signature_file_interrogated = ""
            signature_genes_identifier = ""
            signature_study_type= ""
            signature_description = ""

            signature_controle = ""
            signature_case = ""
            signature_significance = ""
            signature_stat_value = ""
            signature_stat_adjust = ""
            signature_stat_other = ""
            signature_group = ""
            signature_pop_age = ""
            tag = []

            if row_values[1] != "":
                if row_values[1] in studies:
                    signature_associated_study = row_values[1]
                else :
                    signature_error['Critical'].append("Study doesn't exists ("+signature_id+")")
                    critical += 1
            else :
                signature_error['Critical'].append("No associated study ("+signature_id+")")
                critical += 1

            if row_values[2] != "":
                if row_values[2] in assays:
                    signature_associated_assay = row_values[2]
                else :
                    signature_error['Critical'].append("Assay doesn't exists ("+signature_id+")")
                    critical += 1
            else :
                signature_error['Critical'].append("No associated assay ("+signature_id+")")
                critical += 1

            if row_values[3] != "":
                signature_title = row_values[3]
            else :
                signature_error['Critical'].append("No signature title ("+signature_id+")")
                critical += 1

            if row_values[4] != "":
                if row_values[4] in list_signature_type : 
                    signature_type = row_values[4]
                else :
                    signature_error['Critical'].append("Signature title not in the list ("+signature_id+")")
                    critical += 1
            else :
                signature_error['Critical'].append("No type of signature ("+signature_id+")")
                critical += 1

            if row_values[6] != "":
                data = db['species.tab'].find_one({'id': row_values[6]})
                if data is None :
                    if row_values[5] != "":
                        signature_organism_name = row_values[5]
                        tag.append(signature_organism_name)
                    else :
                        signature_organism = ""
                        signature_error['Critical'].append("Please select an organism in the TOXsIgN ontologies list ("+signature_id+")")
                        critical += 1
                else :
                    signature_organism = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[5] != "":
                        signature_organism = row_values[5]
                        tag.append(signature_organism_name)   
            else :
                signature_error['Critical'].append("No organism selected ("+signature_id+")")
                critical += 1

            if row_values[7] != "":
                if row_values[7] in  list_developmental_stage :
                    signature_developmental_stage = row_values[7]
                else :
                    signature_error['Warning'].append("Developmental stage not listed ("+signature_id+")")
            else :
                signature_error['Info'].append("No developmental stage selected ("+signature_id+")")
                

            if row_values[8] != "":
                if row_values[8] in  list_generation :
                    signature_generation = row_values[8]
                else :
                    signature_error['Warning'].append("Generation not listed ("+signature_id+")")
            else :
                signature_error['Info'].append("No generation selected ("+signature_id+")")

            if row_values[9] != "":
                if row_values[9] in  list_sex :
                    signature_sex = row_values[9]
                else :
                    signature_error['Warning'].append("Sex not listed ("+signature_id+")")
            else :
                signature_error['Info'].append("No sex selected ("+signature_id+")")

            if row_values[11] != "":
                data = db['tissue.tab'].find_one({'id': row_values[11]})
                if data is None :
                    if row_values[10] != "":
                        signature_tissue_name = row_values[10]
                        tag.append(signature_tissue_name)
                    else :
                        signature_tissue = ""
                else :
                    signature_tissue = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[10] != "":
                        signature_tissue_name = row_values[10]
                        tag.append(signature_tissue_name)  

            if row_values[13] != "":
                data = db['cell.tab'].find_one({'id': row_values[13]})
                if data is None :
                    if row_values[12] != "":
                        signature_cell_name = row_values[12]
                        tag.append(signature_cell_name)
                    else :
                        signature_cell = ""
                else :
                    signature_cell = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name']) 
                    if row_values[12] != "":
                        signature_cell_name = row_values[12]
                        tag.append(signature_cell_name)  

            if row_values[15] != "":
                data = db['cell_line.tab'].find_one({'id': row_values[15]})
                if data is None :
                    if row_values[14] != "":
                        signature_cell_line_name = row_values[14]
                        tag.append(signature_cell_line_name)
                    else :
                        signature_cell_line = ''
                else :
                    signature_cell_line = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[14] != "":
                        signature_cell_line_name = row_values[14]
                        tag.append(signature_cell_line_name)   

            # Check if at least tissue/cell or cell line are filled
            if signature_cell_line == "" and signature_cell == "" and signature_tissue =="" :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Critical'].append("Please select at least a tissue, cell or cell line in the TOXsIgN ontologies list ("+signature_id+")")
                    critical += 1

            if row_values[17] != "":
                data = db['chemical.tab'].find_one({'id': row_values[17]})
                if data is None :
                    if row_values[16] != "" :
                        signature_molecule_name = row_values[16]
                        tag.append(signature_molecule_name)
                    else :
                        signature_molecule = ""
                else :
                    signature_molecule = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[16] != "" :
                        signature_molecule_name = row_values[16]
                        tag.append(signature_molecule_name)   


            if row_values[18] != "":
                signature_description = row_values[18]
                tag.extend(signature_description)

            if row_values[19] != "":
                data = db['disease.tab'].find_one({'id': row_values[19]})
                if data is None :
                    signature_pathology = ""
                    signature_error['Warning'].append("Pathology / disease not in TOXsIgN ontology ("+signature_id+")")
                else :
                    signature_pathology = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])


            if row_values[21] != "":
                data = db['experiment.tab'].find_one({'id': row_values[21]})
                if data is None :
                    if row_values[20] != "":
                        signature_technology_name = row_values[20]
                        tag.append(signature_technology_name)
                    else :
                        signature_technology = ""
                        if signature_type == "Genomic":
                            signature_error['Warning'].append("Technology not in TOXsIgN ontology ("+signature_id+")")
                else :
                    signature_technology = data['name']
                    tag.append(data['name'])
                    tag.append(data['id'])
                    tag.extend(data['synonyms'])
                    tag.extend(data['direct_parent'])
                    tag.extend(data['all_parent'])
                    tag.extend(data['all_name'])
                    if row_values[20] != "":
                        signature_technology_name = row_values[20]
                        tag.append(signature_technology_name)              
            else :
                if signature_type == "Genomic":
                    signature_error['Warning'].append("No technology selected ("+signature_id+")")

            if row_values[22] != "":
                signature_plateform = row_values[22]
            else :
                if signature_type == "Genomic":
                    signature_error['Info'].append("No plateform selected ("+signature_id+")")


            if row_values[23] != "":
                signature_controle = row_values[23]


            if row_values[24] != "":
                signature_case = row_values[24]


            if row_values[25] != "":
                signature_group = row_values[25]


            if row_values[26] != "":
                signature_group = row_values[26]


            if row_values[27] != "":
                if row_values[27] in  list_observed_effect :
                    signature_observed_effect= row_values[27]
                else :
                    signature_error['Warning'].append("Observed effect not listed ("+signature_id+")")

            if row_values[28] != "":
                signature_significance = row_values[28]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No statistical significance ("+signature_id+")")

            if row_values[29] != "":
                signature_stat_value = row_values[29]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No statistical value ("+signature_id+")")

            if row_values[30] != "":
                signature_stat_adjust = row_values[30]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No statistical adjustment ("+signature_id+")")

            if row_values[31] != "":
                signature_stat_other = row_values[31]





            if row_values[32] != "":
                signature_control_sample = row_values[32]
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Info'].append("No control sample ("+signature_id+")")

            if row_values[33] != "":
                signature_treated_sample = row_values[33]
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Info'].append("No treated sample ("+signature_id+")")

            if row_values[34] != "":
                signature_pvalue = row_values[34]
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Info'].append("No pvalue ("+signature_id+")")

            if row_values[35] != "":
                signature_cutoff = row_values[36]
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Info'].append("No cutoff ("+signature_id+")")

            if row_values[36] != "":
                signature_satistical_processing = row_values[36]
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Info'].append("No statistical processing ("+signature_id+")")

            if row_values[37] != "":
                signature_additional_file = row_values[37]
            else :
                signature_error['Info'].append("No additional file ("+signature_id+")")

            if row_values[38] != "":
                signature_file_up = row_values[38]
            else :
                if signature_type == "Genomic":
                    signature_error['Critical'].append("No signature file (up genes) ("+signature_id+")")
                    critical += 1

            if row_values[39] != "":
                signature_file_down = row_values[39]
            else :
                if signature_type == "Genomic":
                    signature_error['Critical'].append("No signature file (down genes) ("+signature_id+")")
                    critical +=1

            if row_values[40] != "":
                signature_file_interrogated = row_values[40]
            else :
                if signature_type == "Genomic":
                    signature_error['Critical'].append("No signature file (interrogated genes) ("+signature_id+")")
                    critical += 1

            if row_values[41] != "":
                signature_genes_identifier = row_values[41]
            else :
                if signature_type == "Genomic":
                    signature_error['Info'].append("No gene identifier selected ("+signature_id+")")
                    critical += 1

            #After reading line add all info in dico project
            #After reading line add all info in dico project
            db['signature'].update({'id': 1}, {'$inc': {'val': 1}})
            repos = db['signature'].find({'id': 1})
            id_a = ""
            for res in repos:
                id_si = res
            
            #Excel id -> databas id
            asso_id[signature_id] = 'TSS'+str(id_si['val'])
            reverse_asso[asso_id[signature_id]] = signature_id

            #Add signature id to associated assay
            a_signature = assays[signature_associated_assay]['signatures'].split()

            a_signature.append(asso_id[signature_id])
            assays[signature_associated_assay]['signatures'] = ','.join(a_signature)

            #Add factor to the associated study

            s_signature = studies[signature_associated_study]['signatures'].split()
            s_signature.append(asso_id[signature_id])
            studies[signature_associated_study]['signatures'] = ','.join(s_signature)

            #Add factor to the associated project
            project_asso = reverse_asso[studies[signature_associated_study]['projects']]

            p_signature = projects[project_asso]['signatures'].split()
            p_signature.append(asso_id[signature_id])
            projects[project_asso]['signatures'] = ','.join(p_signature)

            #get factors
            tag.extend(assays[signature_associated_assay]['tags'].split(','))
            myset = list(set(tag))
            tag = myset
            
            factor_asso = reverse_asso[assays[signature_associated_assay]['factors']]
            compound_name = factors[factor_asso]["chemical_name"].replace(" ","_").replace(":","").replace("+","and").lower()
            if gse != "GSE48990" :
                if gse == "GSE72081" :
                    if "0.001" in factors[factor_asso]["dose"] :
                        dose = factors[factor_asso]["dose"].replace(" ","").replace("/","")
                    else :
                        dose = factors[factor_asso]["dose"].replace(" ","").replace("/","").replace('.0','')
                else :
                    dose = factors[factor_asso]["dose"].replace(" ","").replace("/","").replace('.0','')
            else : 
                if "10.0" in factors[factor_asso]["dose"]:
                    dose = factors[factor_asso]["dose"].replace(" ","").replace("/","").replace('.0','')
                else :
                    dose = factors[factor_asso]["dose"].replace(" ","").replace("/","")

            
            duration = factors[factor_asso]["exposure_duration"].replace(" ","_").replace('.0','').replace('days','d').replace('hours','h')
            
            print signature_tissue
            if signature_tissue == "" or row_values[10]!='':
            	signature_tissue = row_values[10]
            condName = gse+"+"+signature_tissue.upper().replace(" ","_")+"+"+compound_name+"+"+signature_generation.upper()+"+"+dose+"+"+duration


            dirCond = public_path+studies[signature_associated_study]['projects']+"/"+asso_id[signature_id]
            geneup = []
            genedown = []
            interofile =""
            file_up = ""
            file_down = ""
            os.makedirs(dirCond)
            if condName not in except_files : 
	            upFile = open(projectPath+'/Conditions/'+condName+'_up.txt','r')
	            downFile = open(projectPath+'/Conditions/'+condName+'_down.txt','r')

	            
	            prezfile = 1
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
       
    
                
                
                
            if os.path.isfile(os.path.join(dirCond,signature_plateform)):
                os.remove(os.path.join(dirCond,'genomic_interrogated_genes.txt'))
            interofile = 'genomic_interrogated_genes.txt'
            cmd3 = 'cp %s %s' % (projectPath+"/"+signature_plateform+"_formated.txt",dirCond+'/genomic_interrogated_genes.txt')
            os.system(cmd3)
            
            
            
            upload_path = admin_path
            all_name = asso_id[str(signature_id)]+'.sign'
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

            if len(genedown) == 0 :
                genedown = ""
            else :
                genedown = ','.join(genedown)

            if len(geneup) == 0 :
                geneup = ""
            else :
                geneup = ','.join(geneup)

            signature_study_type = studies[signature_associated_study]['study_type']
            dico ={
                'id' : asso_id[signature_id],
                'studies' : asso_id[signature_associated_study],
                'assays' : asso_id[signature_associated_assay],
                'projects' : studies[signature_associated_study]['projects'] ,
                'title' : signature_title,
                'type' : signature_type,
                'organism' : signature_organism,
                'organism_name' : signature_organism_name,
                'developmental_stage' : signature_developmental_stage,
                'generation' : signature_generation,
                'sex' : signature_sex,
                'last_update' : str(ztime),
                'tissue' : signature_tissue,
                'tissue_name' : signature_tissue_name,
                'cell' : signature_cell,
                'cell_name' : signature_cell_name,
                'status' : 'public',
                'cell_line' : signature_cell_line,
                'cell_line_name' : signature_cell_line_name,
                'molecule' : signature_molecule,
                'molecule_name' : signature_molecule_name,
                'pathology' : signature_pathology,
                'technology' : signature_technology,
                'description' : signature_description,
                'technology_name' : signature_technology_name,
                'plateform' : signature_plateform,
                'observed_effect' : signature_observed_effect,
                'control_sample' : str(signature_control_sample),
                'treated_sample' : str(signature_treated_sample),
                'pvalue' : str(signature_pvalue),
                'cutoff' : str(signature_cutoff),
                'statistical_processing' : "Affymetrix GeneChip data were quality controlled and normalized using using the RMA package with the custom CDF (GPL1355) provided by the BRAINARRAY resource. Next, data analysis was carried out using the Annotation, Mapping, Expression and Network (AMEN) analysis suite of tools (Chalmel & Primig, 2008). Briefly, genes yielding a signal higher than the detection threshold (median of the normalized dataset) and a fold-change >1.5 between exposed and control samples were selected. A Linear Model for Microarray Data (LIMMA) statistical test (F-value adjusted with the False Discovery Rate method: p < 0.05) was employed to identify significantly differentially expressed genes.",
                'additional_file' : signature_additional_file,
                'file_up' : upfile,
                'file_down' : downfile,
                'file_interrogated' : 'genomic_interrogated_genes.txt',
                'genes_identifier': signature_genes_identifier,
                'controle':signature_controle,
                'case':signature_case,
                'significance':signature_significance,
                'stat_val' : signature_stat_value,
                'stat_adjust' : signature_stat_adjust,
                'stat_other' : signature_stat_other,
                'study_type' :signature_study_type,
                'group' : signature_group,
                'pop_age' : signature_pop_age,
                'tags' : ','.join(tag),
                'owner' : user,
                'info' : ','.join(signature_error['Info']),
                'warnings' : ','.join(signature_error['Warning']),
                'critical' : ','.join(signature_error['Critical']),
                'excel_id' : signature_id,
                'genes_up' : geneup,
                'genes_down' : genedown
            }
            signatures[signature_id] = dico
    


    # Create user project directory + move tmp
    for proj in projects :
        ID = projects[proj]['id']
        projects[proj]['edges']  = {}
        for stud in studies:
            projects[proj]['edges'][studies[stud]['id']] = studies[stud]['assays'].split()
        for ass in assays:
            projects[proj]['edges'][assays[ass]['id']] = assays[ass]['signatures'].split()

        projects[proj]['edges'] = json.dumps(projects[proj]['edges'])
        upload_path = public_path+studies[signature_associated_study]['projects']+"/"
        print upload_path
        final_file = 'TOXsIgN_'+ID+'.xlsx'
        cmdX = "cp %s %s" % (input_file,upload_path+final_file)
        os.system(cmdX)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
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




for excel_file in os.listdir(projectPath):
	if ".xlsx" in excel_file :
		gse = excel_file.replace(".xlsx","")
		print gse
		save_excel(projectPath+"/"+excel_file,gse)


