# -*- coding: utf-8 -*-

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden, HTTPUnauthorized
from pyramid.security import remember, forget
from pyramid.renderers import render_to_response
from pyramid.response import Response, FileResponse

import os
import json
from bson import json_util
from bson.objectid import ObjectId
from bson.errors import InvalidId
import jwt
import datetime
import time
import urllib2
import bcrypt
import uuid
import shutil
import zipfile
import tempfile
import copy
import re
import math
import xlrd
from collections import OrderedDict
import simplejson as json
import subprocess
from csv import DictWriter

import logging
import string

import smtplib
import email.utils
import sys
if sys.version < '3':
    from email.MIMEText import MIMEText
else:
    from email.mime.text import MIMEText

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
file_handler = RotatingFileHandler('view.log', 'a', 1000000000, 1)
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



@view_config(route_name='home')
def my_view(request):
    return HTTPFound(request.static_url('chemsign:webapp/app/'))


def send_mail(request, email_to, subject, message):
    if not request.registry.settings['mail.smtp.host']:
        logging.error('email smpt host not set')
        return
    port = 25
    if request.registry.settings['mail.smtp.port']:
        port = int(request.registry.settings['mail.smtp.port'])
    mfrom = request.registry.settings['mail.from']
    mto = email_to
    msg = MIMEText(message)
    msg['To'] = email.utils.formataddr(('Recipient', mto))
    msg['From'] = email.utils.formataddr(('Author', mfrom))
    msg['Subject'] = subject
    server = None
    try:
        server = smtplib.SMTP(request.registry.settings['mail.smtp.host'], request.registry.settings['mail.smtp.port'])
        #server.set_debuglevel(1)
        if request.registry.settings['mail.tls'] and request.registry.settings['mail.tls'] == 'true':
            server.starttls()
        if request.registry.settings['mail.user'] and request.registry.settings['mail.user'] != '':
            server.login(request.registry.settings['mail.user'], request.registry.settings['mail.password'])
        server.sendmail(mfrom, [mto], msg.as_string())
    except Exception as e:
            logging.error('Could not send email: '+str(e))
    finally:
        if server is not None:
            server.quit()


def is_authenticated(request):
    # Try to get Authorization bearer with jwt encoded user information
    if request.authorization is not None:
        try:
            (auth_type, bearer) = request.authorization
            secret = request.registry.settings['secret_passphrase']
            # If decode ok and not expired
            user = jwt.decode(bearer, secret, audience='urn:chemsign/api')
            user_id = user['user']['id']
            user_in_db = request.registry.db_mongo['users'].find_one({'id': user_id})
        except Exception as e:
            return None
        return user_in_db
    return None


@view_config(route_name='user_info', renderer='json', request_method='GET')
def user_info(request):
    user = is_authenticated(request)
    if user is None:
        return HTTPUnauthorized('Not authorized to access this resource')
    if not (user['id'] == request.matchdict['id'] or user['id'] in request.registry.admin_list):
        return HTTPUnauthorized('Not authorized to access this resource')
    user_in_db = request.registry.db_mongo['users'].find_one({'id': request.matchdict['id']})
    return user_in_db

@view_config(route_name='user_info', renderer='json', request_method='POST')
def user_info_update(request):
    user = is_authenticated(request)

    if user['id'] == request.matchdict['id'] or user['id'] in request.registry.admin_list:
        form = json.loads(request.body, encoding=request.charset)
        tid = form['_id']
        token=""
        del form['_id']
        if 'token' in form :
            token = form['token']
            del form['token']
        request.registry.db_mongo['users'].update({'id': request.matchdict['id']}, form)
        form['_id'] = tid
        if token != "" :
            form['token'] = token
        return form
    else :
        return HTTPUnauthorized('Not authorized to access this resource')


@view_config(route_name='user', renderer='json')
def user(request):
    user = is_authenticated(request)
    if user is None or user['id'] not in request.registry.admin_list:
        return HTTPUnauthorized('Not authorized to access this resource')
    users_in_db = request.registry.db_mongo['users'].find()
    users = []
    for user_in_db in users_in_db:
        users.append(user_in_db)
    return users

@view_config(route_name='user_register', renderer='json', request_method='POST')
def user_register(request):
    form = json.loads(request.body, encoding=request.charset)
    if not form['user_name'] or not form['user_password']:
        return {'msg': 'emtpy fields, user name and password are mandatory'}
    user_in_db = request.registry.db_mongo['users'].find_one({'id': form['user_name']})
    if user_in_db is None :
        if 'address' not in form :
            form['address'] = 'No address'
        if 'laboratory' not in form :
            form['laboratory'] = 'No laboratory'
        secret = request.registry.settings['secret_passphrase']
        token = jwt.encode({'user': {'id': form['user_name'],
                                     'password': bcrypt.hashpw(form['user_password'].encode('utf-8'), bcrypt.gensalt()),
                                     'first_name': form['first_name'],
                                     'last_name': form['last_name'],
                                     'laboratory': form['laboratory'],
                                     'country': form['country'],
                                     'address': form['address'],
                                     },
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=36000),
                        'aud': 'urn:chemsign/api'}, secret)
        message = "You requested an account, please click the following link to validate it\n"
        message += request.host_url+'/app/index.html#/login?action=confirm_email&token='+token
        logger.warning(message)
        send_mail(request, form['user_name'], '[ToxSigN] Please validate your account', message)
        return {'msg': 'You will receive a confirmation email. Please click the link to verify your account.'}
    else :
        msg = 'This email is already taken.'
        return {'msg': msg}

@view_config(route_name='user_confirm_email', renderer='json', request_method='POST')
def confirm_email(request):
    form = json.loads(request.body, encoding=request.charset)
    if form and 'token' in form:
        secret = request.registry.settings['secret_passphrase']
        user_id = None
        user_password = None
        try:
            auth = jwt.decode(form['token'], secret, audience='urn:chemsign/api')
            user_id = auth['user']['id']
            user_password = auth['user']['password']
        except Exception:
            return HTTPForbidden()
        status = 'approved'
        msg = 'Email validated, you can now access to your account.'
        if user_id in request.registry.admin_list:
            status = 'approved'
            msg = 'Email validated, you can now log into the application'
        request.registry.db_mongo['users'].insert({'id': user_id,
                                                    'status': status,
                                                    'password': user_password,
                                                    'first_name': auth['user']['first_name'],
                                                    'last_name': auth['user']['last_name'],
                                                    'laboratory': auth['user']['laboratory'],
                                                    'address': auth['user']['address'],
                                                    'avatar': "",
                                                    'selectedID':"",
                                                    })
        upload_path = os.path.join(request.registry.upload_path, user_id, 'dashboard')
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        return {'msg': msg}
    else:
        return HTTPForbidden()

@view_config(route_name='user_validate', renderer='json')
def user_validate(request):
    session_user = is_authenticated(request)
    form = json.loads(request.body, encoding=request.charset)
    if session_user['id'] not in request.registry.admin_list:
        return HTTPForbidden()
    user_id = form['id']
    #print user_id
    request.registry.db_mongo['users'].update({'id': user_id},{'$set': {'status': 'approved'}})
    return {'msg': 'user '+user_id+'validated'}

@view_config(route_name='user_delete', renderer='json')
def user_delete(request):
    session_user = is_authenticated(request)
    form = json.loads(request.body, encoding=request.charset)
    if session_user['id'] not in request.registry.admin_list:
        return HTTPForbidden()
    user_id = form['id']
    if user_id in request.registry.admin_list:
        return {'msg': 'This user is an administrator. Please delete his administrator privileges before'}
    request.registry.db_mongo['users'].remove({'id': user_id})
    request.registry.db_mongo['datasets'].remove({'owner': user_id})
    request.registry.db_mongo['messages'].remove({'owner': user_id})
    return {'msg': 'user '+user_id+'validated'}


@view_config(route_name='user_confirm_recover', renderer='json', request_method='POST')
def user_confirm_recover(request):
    form = json.loads(request.body, encoding=request.charset)
    secret = request.registry.settings['secret_passphrase']
    try:
        auth = jwt.decode(form['token'], secret, audience='urn:chemsign/recover')
        user_id = auth['user']['id']
        user_in_db = request.registry.db_mongo['users'].find_one({'id': user_id})
        if user_in_db is None:
            return HTTPNotFound('User does not exists')
        user_password = form['user_password']
        new_password = bcrypt.hashpw(form['user_password'].encode('utf-8'), bcrypt.gensalt())
        request.registry.db_mongo['users'].update({'id': user_id},{'$set': {'password': new_password}})
    except Exception:
        return HTTPForbidden()
    return {'msg': 'password updated'}


@view_config(route_name='infodatabase', renderer='json', request_method='GET')
def infodatabase(request):
    user = is_authenticated(request)
    if user is None:
        return HTTPUnauthorized('Not authorized to access this resource')
    if not (user['id'] in request.registry.admin_list):
        return HTTPUnauthorized('Not authorized to access this resource')
    project_number = request.registry.db_mongo['projects'].find({'status' :'public'}).count()
    study_number = request.registry.db_mongo['studies'].find({'status' :'public'}).count()
    assay_number = request.registry.db_mongo['assays'].find({'status' :'public'}).count()
    signature_number = request.registry.db_mongo['signatures'].find({'status' :'public'}).count()
    user_request = request.registry.db_mongo['users'].find()
    users = []
    for user in user_request:
        users.append(user)
    pending_request = request.registry.db_mongo['projects'].find({'status' :'pending approval'})
    pendings = []
    for pending in pending_request:
        pendings.append(pending)
    return {'msg':'Database ok','project_number':project_number,'study_number':study_number,'assay_number':assay_number,'signature_number':signature_number,'users':users,'pendings':pendings}

@view_config(route_name='validate', renderer='json', request_method='POST')
def validate(request):
    user = is_authenticated(request)
    if user is None:
        return HTTPUnauthorized('Not authorized to access this resource')
    if not (user['id'] in request.registry.admin_list):
        return HTTPUnauthorized('Not authorized to access this resource')

    form = json.loads(request.body, encoding=request.charset)
    if form['project'] != "" and form['project'] != "gohomo" :
        project = form['project']
        pid = project['id']
        stid = project['studies'].split(',')
        aid = project['assays'].split(',')
        sid = project['signatures'].split(',')
        request.registry.db_mongo['projects'].update({'id' :pid},{'$set':{'status':'public'}})
        request.registry.db_mongo['studies'].update({'id':{ '$all': stid } },{'$set':{'status':'public'}})
        request.registry.db_mongo['assays'].update({'id':{ '$all': aid } },{'$set':{'status':'public'}})
        request.registry.db_mongo['signatures'].update({'id':{ '$all': sid } },{'$set':{'status':'public'}})
        cmd = "python %s --signature a --script gopublic --job b --user none" % (os.path.join(request.registry.script_path, 'jobLauncher.py'))
        os.system(cmd)

        proj = request.registry.db_mongo['projects'].find_one({'id' :pid})
        del proj['_id']
        bulk_insert = ''
        bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"projects\" , \"_id\" : \""+proj['id']+"\" } }\n"
        bulk_insert += json.dumps(proj)+"\n"
        if bulk_insert:
            request.registry.es.bulk(body=bulk_insert)

        for stud in stid:
            study = request.registry.db_mongo['studies'].find_one({'id' :stud})
            del study['_id']
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"studies\" , \"_id\" : \""+study['id']+"\" } }\n"
            bulk_insert += json.dumps(study)+"\n"
            if bulk_insert:
                request.registry.es.bulk(body=bulk_insert)

        for ass in aid:
            assay = request.registry.db_mongo['assays'].find_one({'id' :ass})
            del assay['_id']
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"assays\" , \"_id\" : \""+assay['id']+"\" } }\n"
            bulk_insert += json.dumps(assay)+"\n"
            if bulk_insert:
                request.registry.es.bulk(body=bulk_insert)

        for sign in sid:
            signature = request.registry.db_mongo['signatures'].find_one({'id' :sign})
            del signature['_id']
            bulk_insert = ''
            bulk_insert += "{ \"index\" : { \"_index\" : \"toxsign\", \"_type\": \"signatures\" , \"_id\" : \""+signature['id']+"\" } }\n"
            bulk_insert += json.dumps(signature)+"\n"
            if bulk_insert:
                request.registry.es.bulk(body=bulk_insert)
        return {'msg':'Project status changed : Pending --> public'}

    if form['project'] == "gohomo" :
        cmd = "python %s --signature a --script gohomo --job b --user none" % (os.path.join(request.registry.script_path, 'jobLauncher.py'))
        os.system(cmd)
        return {'msg':'Create annotation file Done'}
    else :
        cmd = "python %s --signature a --script gopublic --job b --user none" % (os.path.join(request.registry.script_path, 'jobLauncher.py'))
        os.system(cmd)
        return {'msg':'Create public.RData Done'}


@view_config(route_name='unvalidate', renderer='json', request_method='POST')
def unvalidate(request):
    user = is_authenticated(request)
    if user is None:
        return HTTPUnauthorized('Not authorized to access this resource')
    if not (user['id'] in request.registry.admin_list):
        return HTTPUnauthorized('Not authorized to access this resource')

    form = json.loads(request.body, encoding=request.charset)
    project = form['project']
    pid = project['id']
    stid = project['studies'].split(',')
    aid = project['assays'].split(',')
    sid = project['signatures'].split(',')
    request.registry.db_mongo['projects'].update({'id' :pid},{'$set':{'status':'private'}})
    request.registry.db_mongo['studies'].update({'id':{ '$all': stid } },{'$set':{'status':'private'}})
    request.registry.db_mongo['assays'].update({'id':{ '$all': stid } },{'$set':{'status':'private'}})
    request.registry.db_mongo['signatures'].update({'id':{ '$all': stid } },{'$set':{'status':'private'}})
    return {'msg':'Project status changed : Pending --> private'}

@view_config(route_name='stat', renderer='json', request_method='GET')
def stat(request):

    # Get project, study, assay and signature number

    projects = request.registry.db_mongo['projects'].find({'status' :'public'}).count()
    studies = request.registry.db_mongo['studies'].find({'status' :'public'}).count()
    assays = request.registry.db_mongo['assays'].find({'status' :'public'}).count()
    signatures = request.registry.db_mongo['signatures'].find({'status' :'public'}).count()

    #Chemical information
    chemical_list = []
    all_factors = request.registry.db_mongo['factors'].find({'status' :'public'})
    for dataset in all_factors :
        if dataset['chemical'] not in chemical_list :
            chemical_list.append(dataset['chemical'])

    # Species & tissue information
    species_list = []
    tissue_list = []
    all_assay = request.registry.db_mongo['assays'].find({'status' :'public'})
    for dataset in all_assay :
        if dataset['tissue'] not in tissue_list :
            tissue_list.append(dataset['tissue'])

    all_spe = request.registry.db_mongo['signatures'].find({'status' :'public'})
    for dataset in all_spe :
        if dataset['organism'] not in species_list :
            species_list.append(dataset['organism'])

    # Nb signatures/species
    sign_spe = {}
    for spe in species_list :
        logger.warning(spe)
        spe_assay = request.registry.db_mongo['signatures'].find( {"organism": spe,'status':'public'}).count()
        sign_spe[spe] = spe_assay

    return {'projects':projects,'studies':studies,'assays':assays,'signatures':signatures,'chemical':str(len(chemical_list)),'species':str(len(species_list)),'tissue':str(len(tissue_list)),'sign_spe':sign_spe}


@view_config(route_name='pending', renderer='json', request_method='POST')
def pending(request):
    user = is_authenticated(request)
    if user is None:
        return HTTPUnauthorized('Not authorized to access this resource')


    form = json.loads(request.body, encoding=request.charset)
    project = form['project']

    if user['id'] != project['owner']:
        return HTTPUnauthorized('Not authorized to access this resource')

    pid = project['id']
    stid = project['studies']
    aid = project['assays']
    sid = project['signatures']
    request.registry.db_mongo['projects'].update({'id' :pid},{'$set':{'status':'pending approval'}})
    request.registry.db_mongo['studies'].update({'id':{ '$all': stid } },{'$set':{'status':'pending approval'}})
    request.registry.db_mongo['assays'].update({'id':{ '$all': stid } },{'$set':{'status':'pending approval'}})
    request.registry.db_mongo['signatures'].update({'id':{ '$all': stid } },{'$set':{'status':'pending approval'}})
    return {'msg':'Your project is now pending approval.'}



@view_config(route_name='1', renderer='json', request_method='POST')
def getdata(request):
    form = json.loads(request.body, encoding=request.charset)
    collection = form['collection']
    select_filter = form['filter']
    field = form['field']
    project_number = 0
    study_number = 0
    assay_number = 0
    signature_number = 0
    if 'all_info' in form :
        project_number = request.registry.db_mongo['projects'].find({field :select_filter}).count()
        study_number = request.registry.db_mongo['studies'].find({field :select_filter}).count()
        assay_number = request.registry.db_mongo['assays'].find({field :select_filter}).count()
        signature_number = request.registry.db_mongo['signatures'].find({field :select_filter}).count()
    if form['from'] == "None" :

        result = request.registry.db_mongo[collection].find_one({field :select_filter})
        if result is not None :
            if 'edges' in result:
                if result['edges'] is not None :
                    if result['edges'] != "" :
                        dico = json.loads(result['edges'])
                        for i in dico :
                            if dico[i] != [] :
                                dico[i] = dico[i][0].split(',')
                        result['edges'] = dico
            return {'msg':'','request':result}
    else :
        selected = []
        if int(form['from']) < 0 :
            form['from'] = 0
        result = request.registry.db_mongo[collection].find({field :select_filter})
        for res in result :
            selected.append(res)
        if len(selected) < int(form['from']) :
            form['from'] = len(selected) - 15
        if len(selected) < int(form['to']) :
            form['to'] = len(selected)
        return {'msg':'ok','request':selected[int(form['from']):int(form['to'])],'project_number':project_number,'study_number':study_number,'assay_number':assay_number,'signature_number':signature_number}

@view_config(route_name='ontologies', renderer='json', request_method='POST')
def ontologies(request):
    form = json.loads(request.body, encoding=request.charset)
    search = form['search']
    database = form['database']
    regx = re.compile(search, re.IGNORECASE)
    repos = request.registry.db_mongo[database].find({"$or":[{'name':regx},{'synonyms':regx}]})
    result = []
    for dataset in repos:
        result.append(dataset)
    return result

@view_config(route_name='getjob', renderer='json', request_method='POST')
def getjob(request):
    form = json.loads(request.body, encoding=request.charset)
    job_list = form['job_list']
    if job_list != "" :
        flist = []
        for i in job_list :
            try:
                flist.append(int(i))
            except:
                continue
        running_job = list(request.registry.db_mongo['Jobs'].find( {"id": {'$in': flist}}))

        return {'jobs':running_job}
    if job_list == "" :
        job = request.registry.db_mongo['Jobs'].find_one( {'_id': ObjectId(form['jid'])})
        return {'jobs':job}

@view_config(route_name='convert', renderer='json', request_method='POST')
def convert(request):
    form = json.loads(request.body, encoding=request.charset)
    genes_list = form['genes'].split(',')
    #print genes_list
    dataset_in_db = ""
    dico_organism = {"Homo sapiens":"9606","Pan troglodytes":"9598","Macaca mulatta":"9544","Canis lupus familiaris":"9615","Bos taurus":"9913","Mus musculus":"10090","Rattus norvegicus":"10116","Gallus gallus":"9031","Xenopus tropicalis":"8364","Danio rerio":"7955"}
    selected_orga = ""
    if form["sign_species"] not in dico_organism :
        selected_orga = "9606"
    else :
        selected_orga = dico_organism[form["sign_species"]]

    if "sign_species" in form:
        #Convert EGesp1 -> HGesp1
        dataset_in_db = list(request.registry.db_mongo['homoloGene'].find( {"Gene_ID": {'$in': genes_list},'Taxonomy_ID':selected_orga},{ "HID": 1, "Gene_Symbol":1,"_id": 0 } ))
        result = []
        for dataset in dataset_in_db:
            if 'NA' not in dataset["HID"]:
                if form["convert_species"] == form["sign_species"]:
                    result.append(str(dataset["HID"])+" ("+str(dataset["Gene_Symbol"])+")")
                else :
                    result.append(dataset["HID"])
        if form["convert_species"] == form["sign_species"]:
            return {'converted_list':result}
        else :
            #Convert HGesp1 -> HGesp2
            dataset_in_db = list(request.registry.db_mongo['homoloGene'].find( {"HID": {'$in': result},'Taxonomy_ID':form["convert_species"]},{ "HID": 1, "Gene_Symbol":1,"_id": 0 } ))
            lresult = []
            for dataset in dataset_in_db:
                if 'NA' not in dataset["HID"]:
                    lresult.append(str(dataset["HID"])+" ("+str(dataset["Gene_Symbol"])+")")
            return {'converted_list':lresult}

    if form['way'] == 'None' or form['way'] == 'EntrezToHomo' :
        if 'species' in form :
            dataset_in_db = list(request.registry.db_mongo['homoloGene'].find( {"Gene_ID": {'$in': genes_list},'Taxonomy_ID':form['species']},{ "HID": 1, "Gene_ID": 1, "Gene_Symbol":1,'Taxonomy_ID':1,"_id": 0 } ))
            result = []
            for dataset in dataset_in_db:
                if 'NA' not in dataset["HID"]:
                    result.append(dataset)
            return {'converted_list':result}
        else :
            dataset_in_db = list(request.registry.db_mongo['genes'].find( {"GeneID": {'$in': genes_list}},{"HID":1, "_id": 0 } ))
            result = []
            for dataset in dataset_in_db:
                if 'NA' not in dataset["HID"]:
                    result.append(dataset["HID"].replace('\n',''))
            #print result
            return {'converted_list':result}
    else :
        dataset_in_db = list(request.registry.db_mongo['homoloGene'].find( {"HID": {'$in': genes_list},'Taxonomy_ID':form['species']},{ "HID": 1, "Gene_ID": 1, "Gene_Symbol":1,'Taxonomy_ID':1,"_id": 0 } ))
        result = []
        for dataset in dataset_in_db:
            if 'NA' not in dataset["Gene_ID"]:
                result.append(dataset)
        return {'converted_list':result}


@view_config(route_name='readresult', renderer='json', request_method='POST')
def readresult(request):
    form = json.loads(request.body, encoding=request.charset)
    jid = form['job']

    job_info = request.registry.db_mongo['Jobs'].find_one({'id':jid})
    result_file = job_info['result']
    if not os.path.isfile(result_file) :
        return {'msg':'No file available','status':"1"}
    param = job_info['arguments'].split(',')
    filter_val = param[0]
    arg_val = param[1]
    value = param[2]
    if job_info['tool'] == "distance analysis" :
        try :
            orgafile = {'pvalue':8,'zscore':6,'r':1}
            if os.path.getsize(result_file) == 0 :
                return {'msg':'No file available','Bp':[],'Disease': [],'Mf':[],'Cc':[] ,'status':"0"}
            else :
                lsg=[]
                fileGo = open(result_file,'r')
                L = fileGo.readlines()
                fileGo.close()

                R = [e.split('\t')  for e in L]#creation list fichier
                #print len(R)
                if arg_val == 'lt' :
                    R = [x for x in R if float(x[orgafile[filter_val]])<=float(value)]

                if arg_val == 'gt' :
                    R = [x for x in R if float(x[orgafile[filter_val]])>=float(value)]


                for line in R :
                    name_sig = request.registry.db_mongo['signatures'].find_one({'id':line[0]})
                    #print line
                    dGo = {'name':line[0]+' - '+name_sig['title'],'signature':line[0],'r':int(line[1]),'R':int(line[2]),'n':int(line[3]),'N':int(line[4]),'rR':line[5],'zscore':line[6],'pvalue':line[7],'pBH':line[8],'euclid':line[9],'cor':line[10],'genes':line[11]}
                    lsg.append(dGo)
                return {'msg':'Enrichment Done','results':lsg,'status':"0"}
        except :
            logger.warning(sys.exc_info())

    if job_info['tool'] == "functional analysis" :
        orgafile = {'pvalue':7,'pbh':8,'r':2,'n':4}
        lbp=[]
        lcc=[]
        lds=[]
        lmf=[]
        fileGo = open(result_file,'r')
        L = fileGo.readlines()
        fileGo.close()

        R = [e.split('\t')  for e in L]#creation list fichier
        #print len(R)
        if arg_val == 'lt' :
            R = [x for x in R if float(x[orgafile[filter_val]])<=float(value)]

        if arg_val == 'gt' :
            R = [x for x in R if float(x[orgafile[filter_val]])>=float(value)]
        #print len(R)
        for line in R :
            dGo = {'Term':line[1],'r':int(line[2]),'R':int(line[3]),'n':int(line[4]),'N':int(line[5]),'rR':float(line[6]),'pvalue':float(line[7]),'pbh':float(line[8])}
            #print dGo
            if line[0] == 'Process' :
                lbp.append(dGo)
            if line[0] == 'Component' :
                lcc.append(dGo)
            if line[0] == 'Phenotype' :
                lds.append(dGo)
            if line[0] == 'Function' :
                lmf.append(dGo)

        return {'msg':'Enrichment Done','Bp':lbp,'Disease': lds,'Mf':lmf,'Cc':lcc ,'status':"0"}

@view_config(route_name='run', renderer='json', request_method='POST')
def run(request):
    form = json.loads(request.body, encoding=request.charset)
    user_id = form['uid']
    arguments = form['arguments']
    tool = form['tool']
    name = form['name']
    signature = json.loads(form['signature'])

    logger.warning("RUNNING")
    logger.warning(form['name'])

    dt = datetime.datetime.utcnow()
    sdt = time.mktime(dt.timetuple())


    if signature is None :
        return {'msg':'Error - TOXsIgn is not able to find your signature. If the problem persists, please contact administrators'}
    else :
        if signature['type'] != 'Genomic' :
            return {'msg':'Error - Your signature is not a genomics signature.','id':'None'}
        if signature['status'] == 'private' and signature['owner'] != user_id :
            return {'msg':'Error - Your are not authorized to access this resource.','id':'None'}

        request.registry.db_mongo['Jobs'].update({'id': 1}, {'$inc': {'val': 1}})
        repos = request.registry.db_mongo['Jobs'].find_one({'id': 1})
        jobID = repos['val']
        if name == "" :
            name = 'TOXsIgN job n°'+str(jobID)
        dico = {
            'id': jobID,
            'name':name,
            'status' : 'creating',
            'user': user_id,
            'tool': tool,
            'signature' :signature['id'],
            'time':sdt,
            'stderr':'',
            'arguments':arguments
        }

        request.registry.db_mongo['Jobs'].insert(dico)
        tool = tool.replace(" ","_")
        cmd = "--signature %s,--script %s,--job %s,--user %s" %(signature['id'],tool,jobID, user_id)
        logger.warning(cmd)
        logger.warning(request.registry.script_path)
        subprocess.Popen(["python", os.path.join(request.registry.script_path, 'jobLauncher.py'),"--signature",str(signature['id']),'--script',tool,'--job',str(jobID),'--user',str(user_id)])
        return {'msg':'Job '+str(jobID)+' submitted','id':jobID}

@view_config(route_name='predict', renderer='json', request_method='POST')
def predict(request):
    def findindex(item2find,listOrString):
        "Search indexes of an item (arg.1) contained in a list or a string (arg.2)"
        return [n for n,item in enumerate(listOrString) if item==item2find]


    form = json.loads(request.body, encoding=request.charset)
    jid = form['job']
    selectedmethod = form['method']
    # FOR TEST uncomment for prod !!!!
    job_info = request.registry.db_mongo['Jobs'].find_one({'id':jid})
    result_file = job_info['result']
    fResults = open(result_file,'r')

    # Test
    dInfo = {}
    groupList = []
    best = {}
    methodList = []
    notCondList = ["Sample",'X','Y']

    #Create dicoTable dico[group][method] = value
    #Create dico Best 
    for lignes in fResults :
        lLingne = lignes.split('\t')

        if lLingne[0] == "Class" :
            for i in lLingne[1:]:
                groupList.append(i)
        

        if lLingne[0] != "Class" and lLingne[0] != "Sample" :
            method = lLingne[0]
            dInfo[method] = {}

            if lLingne[0] not in notCondList:
                methodList.append(method)

            values = lLingne[1:]

            if method == 'X' or method == 'Y' :
                dInfo[method]['groups'] = groupList
                dInfo[method]['values'] = lLingne[1:]

            else :
            
                for item in values :
                    if item == 'NA' :
                        loc = values.index(item)
                        values[loc] = 'nan'
                
                sorted_groups = []
                sorted_value = ""
                if "Correlation" in method :
                    sorted_value = sorted(values,key=lambda x: float('-inf')  if math.isnan(float(x)) else float(x))
                if "Euclidean" in method :
                    sorted_value = sorted(values,key=lambda x: float('inf')  if math.isnan(float(x)) else float(x),reverse=True)
                dInfo[method]['values'] = []

                for val in sorted_value :
                    index_val = findindex(val,values)

                    for indexvalue in index_val :
                        if val != 'nan':
                            dInfo[method]['values'].append(val)
                        if groupList[indexvalue] not in sorted_groups :
                            sorted_groups.append(groupList[indexvalue])
                dInfo[method]['groups'] = sorted_groups
                
                max, min = float("-Inf"),float("Inf")
                maxGroup = minGroup = ""
                for z in range(0,len(values)):
                    group = groupList[z]
                    if values[z] != 'nan' and float(values[z]) > max and group != 'Sign' :
                        max = float(values[z])
                        maxGroup = group
                    if values[z] != 'nan' and float(values[z]) < min and group != 'Sign' :
                        min = float(values[z])
                        minGroup = group
                if "Euclidean" in method :
                    best[method] = minGroup
                if "Correlation" in method :
                    best[method] = maxGroup


    #Set method description
    description = ""
    with open(os.path.join(request.registry.cluster_path,selectedmethod,'description.txt'), 'r') as myfile:
        description=myfile.read().replace('\n', '')

    #Init result dico
    result = {'charts':[],'warning':[],'groups':groupList,'time':'','methods':methodList,'best':best,'description':description,'data':dInfo}  

    for method in methodList :
        #Insert here sorting dictionnary function

        chart = {}
        chart['config']={'displaylogo':False,'modeBarButtonsToRemove':['zoom2d','sendDataToCloud','pan2d','lasso2d','resetScale2d']}
        chart['data']=[]
        chart['description'] = ""
        chart['name'] = method
        chart['title'] = ""
        chart['layout'] = {'height':700,'showlegend': False, 'legend': {'traceorder':'reversed'},'margin':{'l':600}}
        chart['msg'] = []
        data_chart = {}
        data_chart['type'] = 'bar'
        data_chart['orientation'] = "h"
        data_chart['x'] = dInfo[method]['values']
        data_chart['y'] = dInfo[method]['groups']
        chart['data'].append(data_chart)
        result['charts'].append(chart)

    #Scatter plot overview
    chart = {}
    chart['config']={'displaylogo':False,'modeBarButtonsToRemove':['zoom2d','sendDataToCloud','pan2d','lasso2d','resetScale2d']}
    chart['data']=[]
    chart['description'] = ""
    chart['name'] = 'Overview'
    chart['title'] = ""
    chart['layout'] = {'height':700,'showlegend': False, 'legend': {'traceorder':'reversed'}}
    chart['msg'] = []
    data_chart = {}
    data_chart['x'] = []
    data_chart['y'] = []
    data_chart['mode']= 'markers'
    data_chart['type'] = 'scatter'
    data_chart['text'] =  groupList
    data_chart['marker'] ={'size':[],'color':[],'opacity':[]}
    for group in groupList :
        if group in dInfo['X']['groups']:
            if group == "Sign":
                data_chart['marker']['size'].append(20) 
                data_chart['marker']['color'].append(50)
                data_chart['marker']['opacity'].append(1)  
            else :
                data_chart['marker']['size'].append(15) 
                data_chart['marker']['color'].append(10)
                data_chart['marker']['opacity'].append(0.5)

            group_index_x = dInfo['X']['groups'].index(group)
            X_val = dInfo['X']['values'][group_index_x] 
            group_index_y = dInfo['Y']['groups'].index(group)
            Y_val = dInfo['Y']['values'][group_index_y]  
            data_chart['x'].append(X_val)
            data_chart['y'].append(Y_val)

    chart['data'].append(data_chart)
    result['charts'].append(chart)

    #Need to be add at the end
    result['methods'].insert(0,'Overview')
    result['groups'].remove('Sign')
    return result

@view_config(route_name='cluster', renderer='json', request_method='POST')
def cluster(request):
    def convertTime(timetoconvert):
        if timetoconvert == "1_dose":
            return "1 dose"
        if timetoconvert == "1_d":
            return "24h"
        if timetoconvert == "24_hr":
            return "24h"
        if timetoconvert == "2d":
            return "48h"
        if timetoconvert == "3_d":
            return "72h"
        if timetoconvert == "4_day":
            return "96h"
        if timetoconvert == "5_d":
            return "120h"
        if timetoconvert == "7_d":
            return "168h"
        if timetoconvert == "8_day":
            return "192h"
        if timetoconvert == "10d":
            return "240h"
        if timetoconvert == "14_d":
            return "336h"
        if timetoconvert == "15_day":
            return "360h"
        if timetoconvert == "29_day":
            return "696h"
        if timetoconvert == "2_hr":
            return "2h"
        if timetoconvert == "3_hr":
            return "3h"
        if timetoconvert == "6_hr":
            return "6h"
        if timetoconvert == "6h":
            return "6h"
        if timetoconvert == ".25_d":
            return "6h"
        if timetoconvert == "8_hr":
            return "8h"
        if timetoconvert == "9_hr":
            return "9h"
        if timetoconvert == "NA":
            return "Not available"


    form = json.loads(request.body, encoding=request.charset)
    clusterName = form['group'].replace("\n","")
    method = form['method']


    clusterPath = os.path.join(request.registry.cluster_path,method)
    enrichPath = clusterPath+"/Enrichissement/"
    signaturePath = clusterPath+"/Signatures/"
    fCondition = open(clusterPath+"/Groups/"+clusterName+'.txt','r')
    dResults = {'conditions':[],'enrichment':{}}
    lChemicals = []
    for lignes in fCondition.readlines() :
        lignef = lignes.replace('\n','')
        condition_information = lignef.split('+')
        tissue = condition_information[1]
        if tissue == 'LIVER' :
            tissue = 'Liver'
        if tissue == 'KIDNEY' :
            tissue = 'Kidney'
        if tissue == 'HEART' :
            tissue = 'Heart'
        if tissue == 'THIGH-MUSCLE' :
            tissue = 'Skeletal muscle tissue'

        chemical = condition_information[2]
        if chemical.replace('_',' ') not in lChemicals :
            lChemicals.append(chemical.replace('_',' '))
        generation = condition_information[3]
        if '_' in condition_information[4] :
            dose_nb = condition_information[4].split('_')[0]
            dose_unit = condition_information[4].split('_')[1].replace("mgkg",'mg/kg')
            dose = str(dose_nb)+" "+dose_unit
        else :
            dose = condition_information[4].replace('ngmL','ng/mL')
        if '_' in condition_information[5] :
            timeDB = condition_information[5].split('_')
            time_nb = timeDB[0]
            exposure_unit = timeDB[1]
            if timeDB[1] == 'd' :
                exposure_unit = "days"
            if timeDB[1] == 'hr' :
                exposure_unit = "hours"
            if timeDB[1] == 'h' :
                exposure_unit = "hours"
            timeR = time_nb+" "+exposure_unit
            timeC = convertTime(condition_information[5])
        tsaId = request.registry.db_mongo['factors'].find_one({'$and':[{'dose': dose},{'tags':{'$regex' : '.*'+tissue+'.*'}},{'tags':{'$regex' : '.*'+chemical+'.*'}},{'exposure_duration':{'$regex' : '.*'+timeR+'.*'}}]},{ 'assays': 1, '_id': 0 })
        if tsaId is not None :
            tssID = request.registry.db_mongo['assays'].find_one({'id':tsaId['assays']},{ 'signatures': 1, '_id': 0 })
        else :
            tssID = ''
        if lignes.replace('\n','') not in dResults['conditions'] :
            dResults['conditions'].append({'term':lignes.replace('\n',''),'tissue':tissue,'chemical':chemical.replace('_',' '),'generation':generation,'dose':dose,'time':timeC,'id':tssID})
    dResults['enrichment'] = []
    if os.path.isfile(enrichPath+'/'+clusterName+'.chem2enr.txt'):
        fEnr = open(enrichPath+'/'+clusterName+'.chem2enr.txt','r')
        for lignes in fEnr.readlines():
            if lignes.split('\t')[0] != 'MESH' :
                mesh = lignes.split('\t')[0]
                r = lignes.split('\t')[1]
                R = lignes.split('\t')[2]
                n = lignes.split('\t')[3]
                N = lignes.split('\t')[4]
                rR = str(round(float(lignes.split('\t')[5]),6))
                p = str(round(float(lignes.split('\t')[6]),6))
                pBH = str(round(float(lignes.split('\t')[7]),6))
                dResults['enrichment'].append({'mesh':mesh.replace('.',' '),'r':r,'R':R,'n':n,'N':N,'rR':rR,'p':p,'pBH':pBH})
    else :
        dResults['enrichment']= []
        dResults['enrichment'].append({'msg':'No enrichment available'})
    

    print signaturePath+clusterName+'.GeneIDs.txt'
    if os.path.isfile(signaturePath+clusterName+'.GeneIDs.txt'):
        fEnr = open(signaturePath+clusterName+'.GeneIDs.txt','r')
        dResults['signature'] = []
        for lignes in fEnr.readlines():
            dResults['signature'].append(lignes.replace('\n',''))
    else :
        dResults['signature'] = []
        dResults['signature'].append({'msg':'No signature available'})



    return {'msg':'Prediction Done','result':dResults,'chemicalList':lChemicals,'method':form['method'],'cluster':clusterName,'status':"0"}






@view_config(route_name='download', request_method='GET')
def download_data(request):
    session_user = is_authenticated(request)
    dataset_id = request.matchdict['dataset']

    result = request.registry.db_mongo['projects'].find_one({'id' :dataset_id})
    if result['status'] == 'public' :
        name = 'TOXsIgN_'+dataset_id+'.xlsx'
        url_file = os.path.join(request.registry.public_path,dataset_id,name)
        (handle, tmp_file) = tempfile.mkstemp('.zip')
        z = zipfile.ZipFile(tmp_file, "w")
        z.write(url_file,os.path.basename(url_file))
        z.close()
        return FileResponse(tmp_file,
                            request=request,
                            content_type='application/zip')

    if result['status'] == 'private':
        if session_user is None:
            token = None
            try:
                token = request.params['token']
                #print 'TOKEN'
                #print token
            except Exception:
                token = None
            auth = None
            try:
                secret = request.registry.settings['secret_passphrase']
                # If decode ok and not expired
                auth = jwt.decode(token, secret, audience='urn:chemsign/api')
            except Exception as e:
                return HTTPUnauthorized('Not authorized to access this resource')
            if auth is None:
                return HTTPForbidden()
        #print 'PRIVATE'
        #print result['owner']
        #print auth

        if auth['user']['id'] == result['owner'] :
            name = 'TOXsIgN_'+dataset_id+'.xlsx'
            url_file = os.path.join(request.registry.upload_path,result['owner'],dataset_id,name)
            (handle, tmp_file) = tempfile.mkstemp('.zip')
            z = zipfile.ZipFile(tmp_file, "w")
            z.write(url_file,os.path.basename(url_file))
            z.close()
            return FileResponse(tmp_file,
                                request=request,
                                content_type='application/zip')
        else :
            return {'msg':'You are not authorized to access this content'}

@view_config(route_name='file_dataset', request_method='GET')
def file_dataset(request):
    print "Get Dataset"
    logger.warning("Get dataset")
    directory = request.matchdict['dir']
    downfile = request.matchdict['file']
    logger.warning(downfile)
    logger.warning(downfile)
    logger.warning(directory)


    if ".sign." in downfile :
        logger.warning("JOBS")
        logger.warning(downfile)
        logger.warning(directory)
        url_file = os.path.join(request.registry.job_path,directory,downfile)
    else :
        url_file = os.path.join(request.registry.dataset_path,directory,downfile)

    (handle, tmp_file) = tempfile.mkstemp('.zip')
    logger.warning(tmp_file)
    z = zipfile.ZipFile(tmp_file, "w")
    z.write(url_file,os.path.basename(url_file))
    z.close()
    return FileResponse(tmp_file,
                        request=request,
                        content_type='application/zip')




@view_config(route_name='file_signature', request_method='GET')
def file_signature(request):
    session_user = is_authenticated(request)
    dataset_id = request.matchdict['project']
    signature_id = request.matchdict['signature']
    file_id = request.matchdict['file']

    if signature_id == 'none':
        result = ""
        if 'project' in file_id :
            result = request.registry.db_mongo['projects'].find_one({'id' :dataset_id})
        if 'study' in file_id :
            result = request.registry.db_mongo['studies'].find_one({'id' :dataset_id})
        if 'assay' in file_id :
            result = request.registry.db_mongo['assays'].find_one({'id' :dataset_id})
        if 'signature' in file_id :
            result = request.registry.db_mongo['signatures'].find_one({'id' :dataset_id})


        name = file_id+'.csv'
        results = []
        results.append(result)
        header = result.keys()

        file_path = os.path.join(request.registry.upload_path,'tmp')

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        with open(os.path.join(file_path,name),'w') as outfile:
            writer = DictWriter(outfile, header)
            writer.writeheader()
            writer.writerows(results)


        url_file = os.path.join(file_path,name)
        (handle, tmp_file) = tempfile.mkstemp('.zip')
        z = zipfile.ZipFile(tmp_file, "w")
        z.write(url_file,os.path.basename(url_file))
        z.close()
        return FileResponse(tmp_file,
                            request=request,
                            content_type='application/zip')



    result = request.registry.db_mongo['signatures'].find_one({'id' :signature_id})
    if result['status'] == 'public' :
        name = file_id
        url_file = os.path.join(request.registry.public_path,dataset_id,signature_id,name)
        try:
            (handle, tmp_file) = tempfile.mkstemp('.zip')
            z = zipfile.ZipFile(tmp_file, "w")
            z.write(url_file,os.path.basename(url_file))
            z.close()
            return FileResponse(tmp_file,
                                request=request,
                                content_type='application/zip')
        except:
            logger.warning(url_file)
            logger.warning(sys.exc_info())

    if result['status'] == 'private':
        if session_user is None:
            token = None
            try:
                token = request.params['token']
            except Exception:
                token = None
            auth = None
            try:
                secret = request.registry.settings['secret_passphrase']
                # If decode ok and not expired
                auth = jwt.decode(token, secret, audience='urn:chemsign/api')
            except Exception as e:
                return HTTPUnauthorized('Not authorized to access this resource')
            if auth is None:
                return HTTPForbidden()

        if auth['user']['id'] == result['owner'] :
            name = file_id
            url_file = os.path.join(request.registry.upload_path,result['owner'],dataset_id,signature_id,name)
            (handle, tmp_file) = tempfile.mkstemp('.zip')
            z = zipfile.ZipFile(tmp_file, "w")
            z.write(url_file,os.path.basename(url_file))
            z.close()
            return FileResponse(tmp_file,
                                request=request,
                                content_type='application/zip')
        else :
            return {'msg':'You are not authorized to access this content'}

@view_config(route_name='file_upload', renderer='json', request_method='POST')
def file_upload(request):
    session_user = is_authenticated(request)
    logger.warning(request.POST) 
    if session_user is None:
        return 'HTTPForbidden()'
    input_file = None
    try:
        input_file = request.POST['file'].file
    except Exception:
        return HTTPForbidden('no input file')

    signature_selected = request.registry.db_mongo['signatures'].find_one({'id' :request.POST['sid']})
    logger.warning(signature_selected) 

    if signature_selected is None :
        return {'msg':'Something went wrong. If the problem persists, please contact administrators'}
    if signature_selected['owner'] !=  request.POST['uid'] :
        return HTTPForbidden('Not authorized to access this resource')

    if signature_selected[request.POST['type']] == "" :
        request.registry.db_mongo['signatures'].update({'id' :request.POST['sid']},{'$set':{request.POST['type']:request.POST['name']}})
    else :
        if request.POST['name'] not in signature_selected[request.POST['type']] :
            return {'msg':'No file corresponding to your uploaded file. Please update the file name using project updating button'}
        else :
            logger.warning( request.POST['name'])
            logger.warning( signature_selected[request.POST['type']].split())
    logger.warning("ELSE ENTER") 

    if request.POST['type'] == 'additional_file' :
        tmp_file_name = uuid.uuid4().hex
        file_path = os.path.join('/tmp', '%s.sig' % tmp_file_name)
        temp_file_path = file_path + '~'

        # Finally write the data to a temporary file
        with open(temp_file_path, 'wb') as output_file:
            shutil.copyfileobj(input_file, output_file)
        # Now that we know the file has been fully saved to disk move it into place.

        upload_path = os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid'])
        #print upload_path
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        os.rename(temp_file_path, os.path.join(upload_path, request.params['name']))
        print 'write file into : '+ upload_path
        return {'msg':'Upload complete'}
    
    else :
        logger.warning("ELSE ENTER") 
        if signature_selected[request.POST['type']] == "" :
            request.registry.db_mongo['signatures'].update({'id' :request.POST['sid']},{'$set':{request.POST['type']:request.POST['name']}})
        else :
            if request.POST['name'] not in signature_selected[request.POST['type']] :
                return {'msg':'No file corresponding to your uploaded file. Please update the file name using project updating button'}
            else :
                print request.POST['name']
                print signature_selected[request.POST['type']].split()
        try :
            logger.warning(signature_selected['genes_identifier'])
            if signature_selected['genes_identifier'] == 'Entrez genes' :
                logger.warning("OPEN FILE")

                tmp_file_name = uuid.uuid4().hex
                #print tmp_file_name
                file_path = os.path.join('/tmp', '%s.sig' % tmp_file_name)
                temp_file_path = file_path + '~'
                logger.warning(temp_file_path)
                # Finally write the data to a temporary file
                with open(temp_file_path, 'wb') as output_file:
                    shutil.copyfileobj(input_file, output_file)
                # Now that we know the file has been fully saved to disk move it into place.


                logger.warning("FILE write")
                upload_path = os.path.join(request.registry.upload_path, request.params['uid'], 'tmp')

                logger.warning(upload_path)
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                shutil.move(temp_file_path, os.path.join(upload_path, tmp_file_name))
                check_file = open(os.path.join(upload_path, tmp_file_name),'r')


                logger.warning("File OUVERT")
                lId = []
                for lineID in check_file.readlines():
                    if lineID != '' and lineID != 'NA' and lineID != '-' and lineID != 'na' and lineID != ' ' and lineID != 'Na' :
                        IDs = lineID.replace('\n','\t').replace(',','\t').replace(';','\t')
                        lId.append(IDs.split('\t')[0])
                lId = list(set(lId))
                #print lId
                check_file.close()
                dataset_in_db = list(request.registry.db_mongo['genes'].find( {"GeneID": {'$in': lId}},{ "GeneID": 1,"Symbol": 1,"HID":1, "_id": 0 } ))
                lresult = {}
                for i in dataset_in_db:
                    lresult[i['GeneID']]=[i['Symbol'],i['HID']]

                #Create 4 columns signature file
                #print 'test si file'
                if os.path.isfile(os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid'],request.params['name'])):
                    print 'Remove car existes'
                    os.remove(os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid'],request.params['name']))

                ##print 'Remove tmp'
                os.remove(os.path.join(upload_path, tmp_file_name))

                print 'create directory'
                if not os.path.exists(os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid'])):
                    os.makedirs(os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid']))

                #print 'Create final'
                check_files = open(os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'], request.params['sid'],request.params['name']),'a')
                have_wrong = 0
                for ids in lId :
                    if ids in lresult :
                        check_files.write(ids+'\t'+lresult[ids][0]+'\t'+lresult[ids][1].replace('\n','')+'\t1\n')
                    else :
                        check_files.write(ids+'\t'+'NA\tNA'+'\t0\n')
                        have_wrong = 1
                check_files.close()
                #print "File checked and uploded !"
                if 'up' in request.params['type'] :
                    request.registry.db_mongo['signatures'].update({'id' :request.POST['sid']},{'$set':{'genes_up':','.join(lId)}})
                if 'down' in request.params['type'] :
                    request.registry.db_mongo['signatures'].update({'id' :request.POST['sid']},{'$set':{'genes_down':','.join(lId)}})
                if have_wrong == 0 :
                    return {'msg':"File checked and uploded !",'status': '0' }
                else :
                    return {'msg':"Warning ! Some IDs are not EntrezGene ID or are desprecated",'status': '0' }

        except :
            print sys.exc_info()[1]
            return {'msg':"ERROR 023 - TOXsIgN can't read your file. Please make sure you use the correct format. If this error persists, please contact the site administrator.",'status': '1' }

        return {'msg': "ERROR 022 - TOXsIgN can't read your file. Please make sure you use the correct format. If this error persists, please contact the site administrator."}



    #print user
    #print signature_id



@view_config(route_name='excel_upload', renderer='json', request_method='POST')
def excel_signature_upload(request):
    session_user = is_authenticated(request)
    if session_user is None:
        return 'HTTPForbidden()'

    input_file = None
    try:
        input_file = request.POST['file'].file
    except Exception:
        return HTTPForbidden('no input file')

    try :
        tmp_file_name = uuid.uuid4().hex
        file_path = os.path.join('/tmp', '%s.sig' % tmp_file_name)
        temp_file_path = file_path + '~'

        # Finally write the data to a temporary file
        with open(temp_file_path, 'wb') as output_file:
            shutil.copyfileobj(input_file, output_file)
        # Now that we know the file has been fully saved to disk move it into place.

        upload_path = os.path.join(request.registry.upload_path, request.params['uid'], request.params['dataset'])
        #print upload_path
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        shutil.move(temp_file_path, os.path.join(upload_path, tmp_file_name))
        print 'write file into : '+upload_path
    except:
        logger.warning("Error - Upload path")
        logger.warning(upload_path)
        logger.warning(sys.exc_info())
        return {'msg':'An error occurred while uploading your file. If the error persists please contact TOXsIgN support ','status':'1'}

    #Create error list
    project_error = {'Critical':[],'Warning':[],'Info':[]}
    study_error = {'Critical':[],'Warning':[],'Info':[]}
    assay_error = {'Critical':[],'Warning':[],'Info':[]}
    factor_error = {'Critical':[],'Warning':[],'Info':[]}
    signature_error = {'Critical':[],'Warning':[],'Info':[]}
    zorro = 1
    #Read excel file
    try :
        input_file.seek(0)
        wb = xlrd.open_workbook(os.path.join(upload_path, tmp_file_name),encoding_override="cp1251")
        #Read project
        sh = wb.sheet_by_index(0)
        projects={}
        critical = 0
        for rownum in range(5, sh.nrows):
            row_values = sh.row_values(rownum)
            if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                continue
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
            dico ={
                'title' : project_title,
                'description' : project_description,
                'pubmed' : str(project_pubmed.split(',')),
                'contributor' : str(project_contributors.split(','))
            }
            projects[project_id] = dico

        # Check studies
        sh = wb.sheet_by_index(1)
        studies={}
        for rownum in range(6, sh.nrows):
                row_values = sh.row_values(rownum)
                if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                    continue
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
                dico ={
                    'associated_project' : study_projects,
                    'title' : study_title,
                    'description' : study_description,
                    'experimental_design' : study_experimental_design,
                    'results' : study_results,
                    'study_type' : study_type
                }
                studies[study_id] = dico

        # Check assay
        sh = wb.sheet_by_index(2)
        assays={}
        list_developmental_stage = ['Fetal','Embryonic','Larva','Neo-Natal','Juvenile','Pre-pubertal','Pubertal','Adulthood','Elderly','NA']
        list_generation = ['f0','f1','f2','f3','f4','f5','f6','f7','f8','f9','f10']
        list_experimental = ['in vivo','ex vivo','in vitro','other','NA']
        list_sex = ['Male','Female','Both','Other','NA']
        list_dose_unit = ['M','mM','µM','g/mL','mg/mL','µg/mL','ng/mL','mg/kg','µg/kg','µg/kg','ng/kg','%']
        list_exposure_duration_unit = ['week','day','hour','minute','seconde']
        list_exposition_factor = ['Chemical','Physical','Biological']
        list_signature_type = ['Physiological','Genomic','Molecular']
        list_observed_effect = ['Decrease','Increase','No effect','NA']
        for rownum in range(12, sh.nrows):
                row_values = sh.row_values(rownum)
                if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" :
                    continue
                assay_id = row_values[0]
                assay_study = ""
                assay_title = ""
                assay_organism = ""
                assay_experimental_type = ""
                assay_developmental_stage = ""
                assay_generation = ""
                assay_sex = ""
                assay_tissue = ""
                assay_cell = ""
                assay_cell_line = ""
                assay_pop_age = ""
                assay_location = ""
                assay_reference = ""
                assay_matrice = ""
                assay_additional_information = ""


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
                    data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[4]})
                    if data is None :
                        data =  'false'
                        if row_values[3] != "" :
                            data =  'ok'
                            assay_organism = row_values[3]
                    else :
                        data =  'true'
                    if data == 'true' :
                        assay_organism = row_values[4]
                    if data == 'false' :
                        assay_error['Critical'].append("Please select an organism in the TOXsIgN ontologies list ("+assay_id+")")
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
                    data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[9]})
                    if data is None :
                        data =  'false'
                        if row_values[8] != "" :
                            data = 'ok'
                            assay_tissue = row_values[8]
                    else :
                        data = 'true'
                    if data == 'true' :
                        assay_tissue = row_values[9]
                    if data == 'false' :
                        if studies[assay_study]['study_type'] != "Observational":
                            assay_error['Warning'].append("Please select a tissue in the TOXsIgN ontologies list ("+assay_id+")")

                if row_values[11] != "":
                    data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[11]})
                    if data is None :
                        data =  'false'
                        if row_values[10] != "" :
                            data = 'ok'
                            assay_cell = row_values[10]
                    else :
                        data = 'true'
                    if data == 'true' :
                        assay_cell = row_values[11]
                    if data == 'false' :
                        assay_error['Warning'].append("Please select a cell in the TOXsIgN ontologies list ("+assay_id+")")


                if row_values[13] != "":
                    data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[13]})
                    if data is None :
                        data =  'false'
                        if row_values[12] != "" :
                            data = 'ok'
                            assay_cell_line = row_values[12]
                    else :
                        data = 'true'
                    if data == 'true' :
                        assay_cell_line = row_values[13]
                    if data == 'false' :
                        if studies[assay_study]['study_type'] != "Observational":
                            assay_error['Warning'].append("Please select a cell line in the TOXsIgN ontologies list ("+assay_id+")")

                # Check if at least tissue/cell or cell line are filled
                if assay_cell_line == "" and assay_cell == "" and assay_tissue =="" :
                    if studies[assay_study]['study_type'] != "Observational":
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
                dico ={
                    'associated_studies' : assay_study,
                    'title' : assay_title,
                    'organism' : assay_organism,
                    'experimental_type' : assay_experimental_type,
                    'developmental_stage' : assay_developmental_stage,
                    'generation' : assay_generation,
                    'sex' : assay_sex,
                    'tissue' : assay_tissue,
                    'cell' : assay_cell,
                    'cell_line' : assay_cell_line,
                    'additional_information' : assay_additional_information
                }
                assays[assay_id] = dico


        # Check factor
        sh = wb.sheet_by_index(3)
        factors={}
        for rownum in range(5, sh.nrows):
                row_values = sh.row_values(rownum)
                if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" and row_values [4] =="" and row_values [5] =="" :
                    continue
                factor_id = row_values[0]
                factor_type = ""
                factor_assay = ""
                factor_chemical = ""
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

                if row_values[4] != "":
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[4]})
                    if data is None :
                        data =  'false'
                        if row_values[3] != "":
                            data = 'ok'
                            factor_chemical = row_values[3]
                    else :
                        data = 'true'
                    if data == 'true' :
                        factor_chemical = row_values[4]
                    if data == 'false' :
                        factor_error['Warning'].append("Chemical not in the TOXsIgN ontologies list ("+factor_id+")")
                else :
                    assay_error['Warning'].append("No chemical selected ("+factor_id+")")

                if row_values[5] != "":
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[5]})
                    if data is None :
                        data =  'false'
                    else :
                        data = 'true'
                    if data == 'true' :
                        factor_physical = row_values[5]
                    if data == 'false' :
                        a =1
                        #factor_error['Warning'].append("Physical factor not in the TOXsIgN ontologies (not available yet) ("+factor_id+")")
                else :
                    a =1
                    #factor_error['Warning'].append("No physical factor selected (not available yet) ("+factor_id+")")

                if row_values[6] != "":
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[6]})
                    if data is None :
                        data =  'false'
                    else :
                        data = 'true'
                    if data == 'true' :
                        factor_biological = row_values[6]
                    if data == 'true' :
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
                    factor_dose = row_values[9]
                else :
                    factor_error['Critical'].append("Factor dose required ("+factor_id+")")
                    critical += 1

                try :
                    if row_values[10] != "":
                        if str(row_values[10]) in list_dose_unit :
                            factor_dose_unit = str(row_values[10])
                        else :
                            factor_dose_unit = row_values[10]
                    else :
                        factor_error['Critical'].append("Factor dose unit required ("+factor_id+")")
                        critical += 1
                except :
                    factor_dose_unit = row_values[10]

                if row_values[11] != "":
                    factor_exposure_duration = row_values[11]
                else :
                    factor_error['Warning'].append("Factor exposure duration required ("+factor_id+")")
                    critical += 1

                if row_values[12] != "":
                    if row_values[12] in list_exposure_duration_unit :
                        factor_exposure_duration_unit = row_values[12]
                    else :
                        factor_exposure_duration_unit = row_values[12]
                else :
                    factor_error['Critical'].append("Factor dose unit required ("+factor_id+")")
                    critical += 1

                if row_values[13] != "":
                    factor_exposure_frequencies = row_values[13]

                if row_values[14] != "":
                    factor_additional_information = row_values[14]



                #After reading line add all info in dico project
                dico={
                'associated_assay' : factor_assay,
                'type' : factor_type,
                'chemical' : factor_chemical,
                'physical' : factor_physical,
                'biological' : factor_biological,
                'route' : factor_route,
                'vehicle' : factor_vehicle,
                'dose' : factor_dose,
                'dose_unit' : factor_dose_unit,
                'exposure_duration' : factor_exposure_duration,
                'exposure_duration_unit' : factor_exposure_duration_unit,
                'exposure_frequencies' : factor_exposure_frequecies,
                'additional_information' : factor_additional_information
                }
                factors[factor_id] = dico


        # Check signatures
        sh = wb.sheet_by_index(4)
        signatures={}
        for rownum in range(6, sh.nrows):
                row_values = sh.row_values(rownum)
                if row_values [1] == "" and row_values [2] == "" and row_values [3] =="" and row_values [4] =="" and row_values [5] =="" :
                    continue
                signature_id = row_values[0]
                signature_associated_study = ""
                signature_associated_assay = ""
                signature_title = ""
                signature_type = ""
                signature_organism = ""
                signature_developmental_stage = ""
                signature_generation = ""
                signature_sex = ""
                signature_tissue = ""
                signature_cell = ""
                signature_cell_line = ""
                signature_molecule = ""
                signature_pathology = ""
                signature_technology = ""
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
                signature_file_interrogated= ""
                signature_study_type= ""
                signature_genes_identifier = ""
                signature_description = ""

                signature_controle = ""
                signature_case = ""
                signature_significance = ""
                signature_stat_value = ""
                signature_stat_adjust = ""
                signature_stat_other = ""
                signature_group = ""
                signature_pop_age = ""

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
                    data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[6]})
                    if data is None :
                        data =  'false'
                        if row_values[5] != "":
                            data = 'ok'
                            signature_organism = row_values[5]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_organism = row_values[6]
                    if data == 'false' :
                        signature_error['Critical'].append("Please select an organism in the TOXsIgN ontologies list ("+signature_id+")")
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
                    data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[11]})
                    if data is None :
                        data =  'false'
                        if row_values[10] != "":
                            data = 'ok'
                            signature_tissue = row_values[10]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_tissue = row_values[11]
                    if data == 'false' :
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a tissue in the TOXsIgN ontologies list ("+signature_id+")")

                if row_values[13] != "":
                    data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[13]})
                    if data is None :
                        data =  'false'
                        if row_values[12] != "":
                            data = 'ok'
                            signature_cell = row_values[12]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_cell = row_values[13]
                    if data == 'false' :
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a cell in the TOXsIgN ontologies list ("+signature_id+")")


                if row_values[15] != "":
                    data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[15]})
                    if data is None :
                        data =  'false'
                        if row_values[14] != "":
                            data = 'ok'
                            signature_cell_line = row_values[14]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_cell_line = row_values[15]
                    if data == 'false' :
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a cell line in the TOXsIgN ontologies list ("+signature_id+")")

                # Check if at least tissue/cell or cell line are filled
                if signature_cell_line == "" and signature_cell == "" and signature_tissue =="" :
                    if studies[signature_associated_study]['study_type'] != 'Observational' :
                        signature_error['Critical'].append("Please select at least a tissue, cell or cell line in the TOXsIgN ontologies list ("+signature_id+")")
                        critical += 1

                if row_values[17] != "":
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[17]})
                    if data is None :
                        data =  'false'
                        if row_values[16] != "":
                            data = "ok"
                            signature_cell_line = row_values[16]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_molecule = row_values[17]
                    if data == 'false' :
                        signature_error['Warning'].append("Molecule not in TOXsIgN ontology ("+signature_id+")")

                if row_values[18] != "":
                    signature_description = row_values[18]

                if row_values[19] != "":
                    data = request.registry.db_mongo['disease.tab'].find_one({'id': row_values[19]})
                    if data is None :
                        data =  'false'
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_pathology = row_values[19]
                    if data == 'false' :
                        signature_error['Warning'].append("Pathology / disease not in TOXsIgN ontology ("+signature_id+")")

                if row_values[21] != "":
                    data = request.registry.db_mongo['experiment.tab'].find_one({'id': row_values[21]})
                    if data is None :
                        data =  'false'
                        if row_values[20] != "":
                            data = 'ok'
                            signature_technology = row_values[20]
                    else :
                        data = 'true'
                    if data == 'true' :
                        signature_technology = row_values[21]
                    if data == 'false' :
                        if signature_type == "Genomic":
                            signature_error['Warning'].append("Technology not in TOXsIgN ontology ("+signature_id+")")
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
                else :
                    if studies[signature_associated_study]['study_type'] == 'Observational':
                        signature_error['Info'].append("No controle ("+signature_id+")")

                if row_values[24] != "":
                    signature_case = row_values[24]
                else :
                    if studies[signature_associated_study]['study_type'] == 'Observational' :
                        signature_error['Info'].append("No case ("+signature_id+")")

                if row_values[25] != "":
                    signature_group = row_values[25]
                else :
                    if studies[signature_associated_study]['study_type'] == 'Observational' :
                        signature_error['Info'].append("No group ("+signature_id+")")

                if row_values[26] != "":
                    signature_group = row_values[26]
                else :
                    if studies[signature_associated_study]['study_type'] == 'Observational' :
                        signature_error['Info'].append("No population age ("+signature_id+")")



                if row_values[27] != "":
                    if row_values[27] in  list_observed_effect :
                        signature_observed_effect= row_values[27]
                    else :
                        signature_error['Warning'].append("Observed effect not listed ("+signature_id+")")

                else :
                    signature_error['Warning'].append("No observed effect selected ("+signature_id+")")

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
                else :
                    if studies[signature_associated_study]['study_type'] == 'Observational' :
                        signature_error['Info'].append("No statistical information ("+signature_id+")")




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



                signature_study_type = studies[signature_associated_study]
                #After reading line add all info in dico project
                dico={
                    'associated_study' : signature_associated_study,
                    'associated_assay' : signature_associated_assay,
                    'title' : signature_title,
                    'type' : signature_type,
                    'organism' : signature_organism,
                    'developmental_stage' : signature_developmental_stage,
                    'generation' : signature_generation,
                    'sex' : signature_sex,
                    'tissue' : signature_tissue,
                    'cell' : signature_cell,
                    'cell_line' : signature_cell_line,
                    'molecule' : signature_molecule,
                    'pathology' : signature_pathology,
                    'technology' : signature_technology,
                    'plateform' : signature_plateform,
                    'observed_effect' : signature_observed_effect,
                    'control_sample' : signature_control_sample,
                    'treated_sample' : signature_treated_sample,
                    'pvalue' : signature_pvalue,
                    'cutoff' : signature_cutoff,
                    'satistical_processing' : signature_satistical_processing,
                    'additional_file' : signature_additional_file,
                    'file_up' : signature_file_up,
                    'file_down' : signature_file_down,
                    'genes_up' : "",
                    'genes_down' : ""
                }
                signatures[signature_id] = dico



        # Iterate through each row in worksheet and fetch values into dict

        return {'msg':"File checked and uploded !", 'error_project':project_error, 'error_study':study_error, 'error_assay':assay_error, 'error_factor':factor_error, 'error_signature':signature_error, 'critical':str(critical),'file': os.path.join(upload_path, tmp_file_name),'status':'0' }
    except:
        logger.warning("Error - Read excel file")
        logger.warning(sys.exc_info())
        return {'msg':'An error occurred while saving your file. If the error persists please contact TOXsIgN support ','status':'1'}









@view_config(route_name='project_up', renderer='json', request_method='POST')
def save_excel(request):
    session_user = is_authenticated(request)
    if session_user is None:
        return 'HTTPForbidden()'

    input_file = None
    form = json.loads(request.body, encoding=request.charset)
    user = form['uid']

    try:
        input_file = form['file']
    except Exception:
        return HTTPForbidden('no input file')

    print 'write file into : '+input_file

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
    sdt = time.mktime(dt.timetuple())

    try :
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
                request.registry.db_mongo['project'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['project'].find({'id': 1})
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
                    'last_update' : str(sdt),
                    'submission_date' : str(sdt),
                    'status' : 'private' ,
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
                request.registry.db_mongo['study'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['study'].find({'id': 1})
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
                    'last_update' : str(sdt),
                    'inclusion_period': study_inclusion_periode,
                    'inclusion': study_inclusion,
                    'status' : 'private',
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
                    data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[4]})
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
                    data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[9]})
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
                    data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[11]})
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
                    data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[13]})
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
                request.registry.db_mongo['assay'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['assay'].find({'id': 1})
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
                    'status' : 'private',
                    'last_update' : str(sdt),
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

                if row_values[4] != "":
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[4]})
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
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[5]})
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
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[6]})
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
                    factor_dose = row_values[9]
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
                    factor_exposure_duration = row_values[11]
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
                request.registry.db_mongo['factor'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['factor'].find({'id': 1})
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
                        'last_update' : str(sdt),
                        'status' : 'private',
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
                        'last_update' : str(sdt),
                        'status' : 'private',
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
                    data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[6]})
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
                    data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[1]})
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
                    data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[13]})
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
                    data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[15]})
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
                    data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[17]})
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
                    data = request.registry.db_mongo['disease.tab'].find_one({'id': row_values[19]})
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
                    data = request.registry.db_mongo['experiment.tab'].find_one({'id': row_values[21]})
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
                request.registry.db_mongo['signature'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['signature'].find({'id': 1})
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
                    'last_update' : str(sdt),
                    'tissue' : signature_tissue,
                    'tissue_name' : signature_tissue_name,
                    'cell' : signature_cell,
                    'cell_name' : signature_cell_name,
                    'status' : 'private',
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
                    'statistical_processing' : signature_satistical_processing,
                    'additional_file' : signature_additional_file,
                    'file_up' : signature_file_up,
                    'file_down' : signature_file_down,
                    'file_interrogated' : signature_file_interrogated,
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
                    'genes_up' : "",
                    'genes_down' : ""
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
            upload_path = os.path.join(request.registry.upload_path, user, ID)
            final_file = 'TOXsIgN_'+ID+'.xlsx'
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            os.rename(input_file, os.path.join(upload_path, final_file))
            request.registry.db_mongo['projects'].insert(projects[proj])

        for stud in studies:
            request.registry.db_mongo['studies'].insert(studies[stud])

        for ass in assays:
            request.registry.db_mongo['assays'].insert(assays[ass])

        for fac in factors:
            request.registry.db_mongo['factors'].insert(factors[fac])

        for sign in signatures:
            request.registry.db_mongo['signatures'].insert(signatures[sign])


        return {'msg':"File checked and uploded !", 'status':'0'}
    except:
        logger.warning("Error - Save excel file")
        logger.warning(sys.exc_info())
        return {'msg':'An error occurred while uploading your file. If the error persists please contact TOXsIgN support ','status':'1'}





@view_config(route_name='update_dataset', renderer='json', request_method='POST')
def update_dataset(request):
    session_user = is_authenticated(request)
    if session_user is None:
        return 'HTTPForbidden()'

    input_file = None
    form = json.loads(request.body, encoding=request.charset)
    user = form['uid']

    try:
        input_file = form['file']
    except Exception:
        return HTTPForbidden('no input file')
    try:
        pid = form['pid']
    except Exception:
        return HTTPForbidden('no project associated')
    studies = []
    assays = []
    factors = []
    signatres = []

    print 'update file'
    print form['pid']
    p_project = request.registry.db_mongo['projects'].find_one({'id': form['pid']})
    pstudies = p_project['studies'].split(',')
    passays = p_project['assays'].split(',')
    pfactors = p_project['factors'].split(',')
    psignatures = p_project['signatures'].split(',')

    asso_id = {}
    reverse_asso = {}

    #Read excel file
    wb = xlrd.open_workbook(input_file,encoding_override="cp1251")
    #Read project
    sh = wb.sheet_by_index(0)
    projects={}
    critical = 0
    dt = datetime.datetime.utcnow()
    sdt = time.mktime(dt.timetuple())
    try :
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

            if str(row_values[3]) != "" :
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

            #Excel id -> databas id
            asso_id[project_id] =  p_project['id']
            reverse_asso[asso_id[project_id]] = project_id

            dico={
                'id' : p_project['id'],
                'title' : project_title,
                'description' : project_description,
                'pubmed' : project_pubmed,
                'contributor' : project_contributors,
                'cross_link' : project_crosslink,
                'assays' : "",
                'studies' : "",
                'factors' : "",
                'signatures' :"",
                'last_update' : str(sdt),
                'submission_date' : str(sdt),
                'status' : 'private' ,
                'owner' : user,
                'author' : user ,
                'tags' : "",
                'edges' : "",
                'info' : ','.join(project_error['Info']),
                'warnings' : ','.join(project_error['Warning']),
                'critical' : ','.join(project_error['Critical']),
                'excel_id' : project_id
                }

            if p_project['excel_id'] == project_id :
                projects[project_id] = dico
            else :
                return {'msg':'Error in template format (project id ?) '}

        # Check studies
        sh = wb.sheet_by_index(1)
        studies={}
        l_excelId = []
        for stud in pstudies :
            study = request.registry.db_mongo['studies'].find_one({'id': stud})
            if study is not None :
                l_excelId.append(study['excel_id'])


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

                if study_id in l_excelId :
                    for stud in pstudies :
                        if study is not None :
                            study = request.registry.db_mongo['studies'].find_one({'id': stud})
                            if study['excel_id'] == study_id :

                                asso_id[study_id] = study['id']
                                reverse_asso[asso_id[study_id]] = study_id

                                #Add studies id to associated project
                                p_stud = projects[study_projects]['studies'].split()
                                p_stud.append(asso_id[study_id])
                                p_stud = list(set(p_stud))
                                projects[study_projects]['studies'] = ','.join(p_stud)

                                dico={
                                    'id' : study['id'],
                                    'owner' : user,
                                    'projects' : asso_id[study_projects],
                                    'assays' : "",
                                    'factors' : "",
                                    'status' : 'private' ,
                                    'signatures' : study['signatures'],
                                    'title' : study_title,
                                    'description' : study_description,
                                    'experimental_design' : study_experimental_design,
                                    'results' : study_results,
                                    'study_type' : study_type,
                                    'last_update' : str(sdt),
                                    'inclusion_period': study_inclusion_periode,
                                    'inclusion': study_inclusion,
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

                                studies[study_id] = dico
                else :

                    #After reading line add all info in dico project
                    request.registry.db_mongo['study'].update({'id': 1}, {'$inc': {'val': 1}})
                    repos = request.registry.db_mongo['study'].find({'id': 1})
                    id_s = ""
                    for res in repos:
                        id_s = res

                    #Excel id -> databas id
                    asso_id[study_id] = 'TSE'+str(id_s['val'])
                    reverse_asso[asso_id[study_id]] = study_id

                    p_stud = projects[study_projects]['studies'].split()
                    p_stud.append(asso_id[study_id])
                    p_stud = list(set(p_stud))
                    projects[study_projects]['studies'] = ','.join(p_stud)

                   #Excel id -> databas id


                    dico={
                        'id' : asso_id[study_id],
                        'owner' : user,
                        'projects' : asso_id[study_projects],
                        'assays' : "",
                        'factors' : "",
                        'status' : 'private' ,
                        'signatures' : "",
                        'title' : study_title,
                        'description' : study_description,
                        'experimental_design' : study_experimental_design,
                        'results' : study_results,
                        'study_type' : study_type,
                        'last_update' : str(sdt),
                        'inclusion_period': study_inclusion_periode,
                        'inclusion': study_inclusion,
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
        assays_up = {}
        l_excelId = []
        for ass in passays :
            assay = request.registry.db_mongo['assays'].find_one({'id': ass})
            if assay is not None :
                if assay['excel_id'] is not None :
                    l_excelId.append(assay['excel_id'])
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
                data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[4]})
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
                data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[9]})
                if data is None :
                    if row_values[8] != "":
                        assay_tissue_name = row_values[8]
                        tag.append(assay_tissue_name)
                    else :
                        assay_tissue = ""

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
                data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[11]})
                if data is None :
                    if row_values[10] != "":
                        assay_cell_name = row_values[10]
                        tag.append(assay_cell_name)
                    else :
                        assay_cell = ""

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
                data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[13]})
                if data is None :
                    if row_values[12] != "":
                        assay_cell_line_name = row_values[12]
                        tag.append(assay_cell_line_name)
                    else :
                        assay_cell_line = ""
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
                if studies[assay_study]['study_type'] =='Observational' :
                    assay_error['Critical'].append("Please select at least a tissue, cell or cell line in the TOXsIgN ontologies list ("+assay_id+")")
                    critical += 1

            if row_values[14] != "":
                if row_values[14] in  list_experimental :
                    assay_experimental_type = row_values[14]
                else :
                    assay_error['Warning'].append("Experimental type not listed ("+assay_id+")")


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
            else :
                assay_error['Info'].append("No additional information ("+assay_id+")")

            if assay_id in l_excelId :
                for ass in passays :
                    assay = request.registry.db_mongo['assays'].find_one({'id': ass})
                    if assay is not None :
                        if assay['excel_id'] == assay_id :

                            asso_id[assay_id] = assay['id']
                            reverse_asso[asso_id[assay_id]] = assay_id

                            #Add assay id to associated study
                            s_assay = studies[assay_study]['assays'].split()
                            s_assay.append(asso_id[assay_id])
                            s_assay = list(set(s_assay))
                            studies[assay_study]['assays'] = ','.join(s_assay)

                            #Add assay to the associated project
                            project_asso = reverse_asso[studies[assay_study]['projects']]

                            p_assay = projects[project_asso]['assays'].split()
                            p_assay.append(asso_id[assay_id])
                            p_assay = list(set(p_assay))
                            projects[project_asso]['assays'] = ','.join(p_assay)

                            dico={
                                'id' : assay['id'] ,
                                'studies' : asso_id[assay_study],
                                'factors' : "",
                                'signatures' : "",
                                'status' : 'private' ,
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
                                'last_update' : str(sdt),
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
            else :

                #After reading line add all info in dico project
                request.registry.db_mongo['assay'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['assay'].find({'id': 1})
                id_a = ""
                for res in repos:
                    id_a = res

                #Excel id -> databas id
                asso_id[assay_id] = 'TSA'+str(id_a['val'])
                reverse_asso[asso_id[assay_id]] = assay_id


                #Add assay id to associated study
                s_assay = studies[assay_study]['assays'].split()
                s_assay.append(asso_id[assay_id])
                s_assay = list(set(s_assay))
                studies[assay_study]['assays'] = ','.join(s_assay)

                #Add assay to the associated project
                project_asso = reverse_asso[studies[assay_study]['projects']]

                p_assay = projects[project_asso]['assays'].split()
                p_assay.append(asso_id[assay_id])
                p_assay = list(set(p_assay))
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
                    'status' : 'private',
                    'last_update' : str(sdt),
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

        l_excelId = []
        for fact in pfactors :
            factor = request.registry.db_mongo['factors'].find_one({'id': fact})
            l_excelId.append(factor['excel_id'])

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

            if row_values[4] != "":
                data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[4]})
                if data is None :
                    if row_values[3] != "":
                        factor_chemical_name = row_values[3]
                        tag.append(factor_chemical_name)
                    else :
                        factor_chemical = ""
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

            if row_values[5] != "":
                data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[5]})
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
                data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[6]})
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
                factor_dose = row_values[9]
            else :
                factor_error['Critical'].append("Factor dose required ("+factor_id+")")
                critical += 1

            try :
                if row_values[10] != "":
                    if str(row_values[10]) in list_dose_unit :
                        factor_dose_unit = row_values[10]
                    else :
                        factor_error['Warning'].append("Dose unit not in list ("+factor_id+")")
                else :
                    factor_error['Critical'].append("Factor dose unit required ("+factor_id+")")
                    critical += 1
            except :
                 factor_dose_unit = row_values[10]

            if row_values[11] != "":
                factor_exposure_duration = row_values[11]
            else :
                factor_error['Critical'].append("Factor exposure duration required ("+factor_id+")")
                critical += 1

            try :
                if row_values[12] != "":
                    if str(row_values[12]) in list_exposure_duration_unit :
                        factor_exposure_duration_unit = row_values[12]
                    else :
                        factor_error['Critical'].append("Exposure duration unit not in list ("+factor_id+")")
                        critical += 1
                else :
                    factor_error['Critical'].append("Factor dose unit required ("+factor_id+")")
                    critical += 1
            except :
                factor_exposure_duration_unit = row_values[12]

            if row_values[13] != "":
                factor_exposure_frequecies = row_values[13]
            else :
                factor_error['Warning'].append("No exposure frequencies ("+factor_id+")")

            if row_values[14] != "":
                factor_additional_information = row_values[14]
            else :
                factor_error['Info'].append("No additional information ("+factor_id+")")

            if factor_id in l_excelId :
                for fact in pfactors :
                    factor = request.registry.db_mongo['factors'].find_one({'id': fact})
                    if factor['excel_id'] == factor_id :

                        asso_id[factor_id] = factor['id']
                        reverse_asso[asso_id[factor_id]] = factor_id

                        #Add factor id to associated assay
                        a_factor = assays[factor_assay]['factors'].split()
                        a_factor.append(asso_id[factor_id])
                        a_factor = list(set(a_factor))
                        assays[factor_assay]['factors'] = ','.join(a_factor)

                        #Add factor to the associated study
                        study_asso = reverse_asso[assays[factor_assay]['studies']]

                        s_factor = studies[study_asso]['factors'].split()
                        s_factor.append(asso_id[factor_id])
                        s_factor = list(set(s_factor))
                        studies[study_asso]['factors'] = ','.join(s_factor)

                        #Add factor to the associated project
                        project_asso = reverse_asso[assays[factor_assay]['projects']]

                        p_factor = projects[project_asso]['factors'].split()
                        p_factor.append(asso_id[factor_id])
                        p_factor = list(set(p_factor))
                        projects[project_asso]['factors'] = ','.join(p_factor)

                        #up factor tags to associated assy
                        tag_assay = assays[factor_assay]['tags'].split(',')
                        tag_assay.extend(tag)
                        tag_assay = list(set(tag_assay))
                        assays[factor_assay]['tags'] = ','.join(tag_assay)

                        dico={
                            'id' : factor['id'],
                            'assays' : asso_id[factor_assay],
                            'studies' : assays[factor_assay]['studies'],
                            'project' : assays[factor_assay]['projects'],
                            'type' : factor_type,
                            'status' : 'private' ,
                            'chemical' : factor_chemical,
                            'chemical_name' : factor_chemical_name,
                            'physical' : factor_physical,
                            'biological' : factor_biological,
                            'route' : factor_route,
                            'last_update' : str(sdt),
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

                        factors[factor_id] = dico

            else :

                #After reading line add all info in dico project
                request.registry.db_mongo['factor'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['factor'].find({'id': 1})
                id_a = ""
                for res in repos:
                    id_f = res

                #Excel id -> databas id
                asso_id[factor_id] = 'TSF'+str(id_f['val'])
                reverse_asso[asso_id[factor_id]] = factor_id

                #Add factor id to associated assay
                a_factor = assays[factor_assay]['factors'].split()
                a_factor.append(asso_id[factor_id])
                a_factor = list(set(a_factor))
                assays[factor_assay]['factors'] = ','.join(a_factor)

                #Add factor to the associated study
                study_asso = reverse_asso[assays[factor_assay]['studies']]

                s_factor = studies[study_asso]['factors'].split()
                s_factor.append(asso_id[factor_id])
                s_factor = list(set(s_factor))
                studies[study_asso]['factors'] = ','.join(s_factor)

                #Add factor to the associated project
                project_asso = reverse_asso[assays[factor_assay]['projects']]

                p_factor = projects[project_asso]['factors'].split()
                p_factor.append(asso_id[factor_id])
                p_factor = list(set(p_factor))
                projects[project_asso]['factors'] = ','.join(p_factor)

                #up factor tags to associated assy
                tag_assay = assays[factor_assay]['tags'].split(',')
                tag_assay.extend(tag)
                tag_assay = list(set(tag_assay))
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
                        'last_update' : str(sdt),
                        'status' : 'private',
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
                except:
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
                        'last_update' : str(sdt),
                        'status' : 'private',
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
        l_excelId = []
        for sign in psignatures :
            signature = request.registry.db_mongo['signatures'].find_one({'id': sign})
            l_excelId.append(signature['excel_id'])
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
                data = request.registry.db_mongo['species.tab'].find_one({'id': row_values[6]})
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
                data = request.registry.db_mongo['tissue.tab'].find_one({'id': row_values[1]})
                if data is None :
                    if row_values[10] != "":
                        signature_tissue_name = row_values[10]
                        tag.append(signature_tissue_name)
                    else :
                        signature_tissue = ""
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a tissue in the TOXsIgN ontologies list ("+signature_id+")")
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
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Warning'].append("No tissue selected ("+signature_id+")")

            if row_values[13] != "":
                data = request.registry.db_mongo['cell.tab'].find_one({'id': row_values[13]})
                if data is None :
                    if row_values[12] != "":
                        signature_cell_name = row_values[12]
                        tag.append(signature_cell_name)
                    else :
                        signature_cell = ""
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a cell in the TOXsIgN ontologies list ("+signature_id+")")
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
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Warning'].append("No cell selected ("+signature_id+")")


            if row_values[15] != "":
                data = request.registry.db_mongo['cell_line.tab'].find_one({'id': row_values[15]})
                if data is None :
                    if row_values[14] != "":
                        signature_cell_line_name = row_values[14]
                        tag.append(signature_cell_line_name)
                    else :
                        signature_cell_line = 'No cell line'
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            signature_error['Warning'].append("Please select a cell line in the TOXsIgN ontologies list ("+signature_id+")")
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
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Warning'].append("No cell line selected ("+signature_id+")")

            # Check if at least tissue/cell or cell line are filled
            if signature_cell_line == "" and signature_cell == "" and signature_tissue =="" :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    signature_error['Critical'].append("Please select at least a tissue, cell or cell line in the TOXsIgN ontologies list ("+signature_id+")")
                    critical += 1

            if row_values[17] != "":
                data = request.registry.db_mongo['chemical.tab'].find_one({'id': row_values[17]})
                if data is None :
                    if row_values[16] != "" :
                        signature_molecule_name = row_values[16]
                        tag.append(signature_molecule_name)
                    else :
                        signature_molecule = ""
                        if studies[signature_associated_study]['study_type'] != 'Observational' :
                            if signature_type == "Molecular":
                                signature_error['Warning'].append("Molecule not in TOXsIgN ontology ("+signature_id+")")
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
            else :
                if studies[signature_associated_study]['study_type'] != 'Observational' :
                    if signature_type == "Molecular":
                        signature_error['Warning'].append("No molecule selected ("+signature_id+")")

            if row_values[18] != "":
                signature_description = row_values[18]

            if row_values[19] != "":
                data = request.registry.db_mongo['disease.tab'].find_one({'id': row_values[19]})
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

            else :
                signature_error['Warning'].append("No pathology / disease selected ("+signature_id+")")

            if row_values[21] != "":
                data = request.registry.db_mongo['experiment.tab'].find_one({'id': row_values[21]})
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
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational':
                    signature_error['Info'].append("No controle ("+signature_id+")")

            if row_values[24] != "":
                signature_case = row_values[24]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational':
                    signature_error['Info'].append("No case ("+signature_id+")")

            if row_values[25] != "":
                signature_group = row_values[25]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No group ("+signature_id+")")

            if row_values[26] != "":
                signature_group = row_values[26]
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No population age ("+signature_id+")")


            if row_values[27] != "":
                if row_values[27] in  list_observed_effect :
                    signature_observed_effect= row_values[27]
                else :
                    signature_error['Warning'].append("Observed effect not listed ("+signature_id+")")

            else :
                signature_error['Warning'].append("No observed effect selected ("+signature_id+")")

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
            else :
                if studies[signature_associated_study]['study_type'] == 'Observational' :
                    signature_error['Info'].append("No statistical information ("+signature_id+")")




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

            signature_study_type = studies[signature_associated_study]
            if signature_id in l_excelId :
                for sign in psignatures :
                    signature = request.registry.db_mongo['signatures'].find_one({'id': sign})
                    if signature['excel_id'] == signature_id :

                        asso_id[signature_id] = signature['id']
                        reverse_asso[asso_id[signature_id]] = signature_id

                        a_signature = assays[signature_associated_assay]['signatures'].split()

                        a_signature.append(asso_id[signature_id])
                        a_signature = list(set(a_signature))
                        assays[signature_associated_assay]['signatures'] = ','.join(a_signature)

                        #Add factor to the associated study

                        s_signature = studies[signature_associated_study]['signatures'].split()
                        s_signature.append(asso_id[signature_id])
                        s_signature = list(set(s_signature))
                        studies[signature_associated_study]['signatures'] = ','.join(s_signature)

                        #Add factor to the associated project
                        project_asso = reverse_asso[studies[signature_associated_study]['projects']]

                        p_signature = projects[project_asso]['signatures'].split()
                        p_signature.append(asso_id[signature_id])
                        p_signature = list(set(p_signature))
                        projects[project_asso]['signatures'] = ','.join(p_signature)

                        #get factors
                        tag.extend(assays[signature_associated_assay]['tags'].split(','))
                        myset = list(set(tag))
                        tag = myset


                        dico={
                        'id' : signature['id'],
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
                        'last_update' : str(sdt),
                        'tissue' : signature_tissue,
                        'tissue_name' : signature_tissue_name,
                        'cell' : signature_cell,
                        'cell_name' : signature_cell_name,
                        'status' : 'private',
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
                        'statistical_processing' : signature_satistical_processing,
                        'additional_file' : signature_additional_file,
                        'file_up' : signature_file_up,
                        'file_down' : signature_file_down,
                        'file_interrogated' : signature_file_interrogated,
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
                        'genes_up' : "",
                        'genes_down' : ""
                        }

                        signatures[signature_id] = dico

            else :
                #After reading line add all info in dico project
                request.registry.db_mongo['signature'].update({'id': 1}, {'$inc': {'val': 1}})
                repos = request.registry.db_mongo['signature'].find({'id': 1})
                id_a = ""
                for res in repos:
                    id_si = res

                #Excel id -> databas id
                asso_id[signature_id] = 'TSS'+str(id_si['val'])
                reverse_asso[asso_id[signature_id]] = signature_id

                a_signature = assays[signature_associated_assay]['signatures'].split()

                a_signature.append(asso_id[signature_id])
                a_signature = list(set(a_signature))
                assays[signature_associated_assay]['signatures'] = ','.join(a_signature)

                #Add factor to the associated study

                s_signature = studies[signature_associated_study]['signatures'].split()
                s_signature.append(asso_id[signature_id])
                s_signature = list(set(s_signature))
                studies[signature_associated_study]['signatures'] = ','.join(s_signature)

                #Add factor to the associated project
                project_asso = reverse_asso[studies[signature_associated_study]['projects']]

                p_signature = projects[project_asso]['signatures'].split()
                p_signature.append(asso_id[signature_id])
                p_signature = list(set(p_signature))
                projects[project_asso]['signatures'] = ','.join(p_signature)

                #get factors
                tag.extend(assays[signature_associated_assay]['tags'].split(','))
                myset = list(set(tag))
                tag = myset

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
                    'last_update' : str(sdt),
                    'tissue' : signature_tissue,
                    'tissue_name' : signature_tissue_name,
                    'cell' : signature_cell,
                    'cell_name' : signature_cell_name,
                    'status' : 'private',
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
                    'statistical_processing' : signature_satistical_processing,
                    'additional_file' : signature_additional_file,
                    'file_up' : signature_file_up,
                    'file_down' : signature_file_down,
                    'file_interrogated' : signature_file_interrogated,
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
                    'genes_up' : "",
                    'genes_down' : ""
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
            request.registry.db_mongo['projects'].update({'id': projects[proj]['id']},projects[proj])

        upload_path = os.path.join(request.registry.upload_path, user, form['pid'])
        final_file = 'TOXsIgN_'+form['pid']+'.xlsx'
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
        os.rename(input_file, os.path.join(upload_path, final_file))

        for stud in studies:
            get = request.registry.db_mongo['studies'].find_one({'id': studies[stud]['id']})
            if get is None :
                request.registry.db_mongo['studies'].insert(studies[stud])
            else :
                request.registry.db_mongo['studies'].update({'id': studies[stud]['id']},studies[stud])

        for ass in assays:
            get = request.registry.db_mongo['assays'].find_one({'id': assays[ass]['id']})
            if get is None :
                request.registry.db_mongo['assays'].insert(assays[ass])
            else :
                request.registry.db_mongo['assays'].update({'id': assays[ass]['id']},assays[ass])

        for fac in factors:
            get = request.registry.db_mongo['factors'].find_one({'id': factors[fac]['id']})
            if get is None :
                request.registry.db_mongo['factors'].insert(factors[fac])
            else :
                request.registry.db_mongo['factors'].update({'id': factors[fac]['id']},factors[fac])

        for sign in signatures:
            get = request.registry.db_mongo['signatures'].find_one({'id': signatures[sign]['id']})
            if get is None :
                request.registry.db_mongo['signatures'].insert(signatures[sign])
            else :
                request.registry.db_mongo['signatures'].update({'id': signatures[sign]['id']},signatures[sign])


        return {'msg':"File checked and update !" }

    except:
        logger.warning("Error - Upadate excel file")
        logger.warning(sys.exc_info())
        return {'msg':'An error occurred while updating your file. If the error persists please contact TOXsIgN support ','status':'1'}






def changeQuery(query,_type):
    test=query
    #print test
    wordList = re.sub("[^\w]", " ",  test).split()
    newList=[]
    for elt in wordList:
        if re.search("^[aA][nN][dD]$", elt):
            newList.append("AND")
        elif re.search("^[oO][rR]$",elt):
            newList.append("OR")
        else:
        # if elt != "AND" and elt != "OR":
            newList.append("(_type:"+_type+" AND _all:*"+elt+'*)')
        # else:
        #     newList.append(elt)
    start=0
    newString=""
    for i in range(len(wordList)):
        if wordList[i] != "AND" and wordList[i]!="OR":
            index=test.find(wordList[i])
            stop=index+(len(wordList[i]))
            substr=test[index:stop]
            newindex=stop
            chaine=string.replace(substr,str(wordList[i]), str(newList[i]))
            try:
                if (test[index-1] == '('):
                    chaine='('+chaine
                if (test[stop] == ')'):
                    chaine=chaine+')'
                newString+=chaine
            except:
                newString+=chaine

        else:
            newString+= ' '+ wordList[i] + ' '

    return newString



@view_config(route_name='search', renderer='json', request_method='POST')
def search(request):
    form = json.loads(request.body, encoding=request.charset)
    request_query = form['query']


    size=25


    #return {'query':request_query}

    if 'search' in form:

        query=form['query']
        pfrom=form['pfrom']
        sfrom=form['sfrom']
        sgfrom=form['sgfrom']
        query_project=changeQuery(query,'projects')
        query_study=changeQuery(query,'studies')
        query_signature=changeQuery(query,'signatures')

        # return {'query_project':query_project, 'query_study':query_study, 'query_signature':query_signature}



        # page=request.registry.es.search(
        #     index = request.registry.es_db,
        #     search_type = 'query_then_fetch',
        #     size = size,
        #     from_= from_val,
        #     body = {"query" : { "query_string" : {"query" :'_type:_all AND ' +request_query,"default_operator":"AND",'analyzer': "standard"}}})


        project = request.registry.es.search(
            index = request.registry.es_db,
            search_type = 'query_then_fetch',
            from_= pfrom,
            size = size,
            body = {"query" : { "query_string" : {"query" :query_project,"default_operator":"AND",'analyzer': "standard"}}})

        study = request.registry.es.search(
            index = request.registry.es_db,
            search_type = 'query_then_fetch',
            from_= sfrom,
            size = size,
            body = {"query" : { "query_string" : {"query" :query_study,"default_operator":"AND",'analyzer': "standard"}}})

        signature = request.registry.es.search(
            index = request.registry.es_db,
            search_type = 'query_then_fetch',
            from_= sgfrom,
            size = size,
            body = {"query" : { "query_string" : {"query" :query_signature,"default_operator":"AND",'analyzer': "standard"}}})


        number_project=str(project['hits']['total'])
        if number_project=="0":
            number_project="No Result"

        number_study=str(study['hits']['total'])
        if number_study=="0":
            number_study="No result"

        number_signature=str(signature['hits']['total'])
        if number_signature=="0":
            number_signature="No Result"


        return {'projects' : project, 'studies':study , 'signatures' : signature ,'query': query_project, \
                    'number_project' : number_project, 'number_study' : number_study,\
                    'number_signature' :number_signature, 'query':query}
        # return page

    request_number_query=form['number_query']
    request_pfrom=form['pfrom']
    request_sfrom=form['sfrom']
    request_sgfrom=form['sgfrom']

    if request_pfrom<0:
        request.pfrom=0
    # if 'from' in form :
    #     from_val = form['from']
    # else :
    #     from_val = 0

    if request_query == '(_all:*) ':
        return {'query':request_query}

    elif request_number_query == 1:
        # page= request.registry.es.search(index = request.registry.es_db) \
        # .filter("term", category="search") \
        # .query("kidney", title="title")
        if('projects' in request_query):
            _from=request_pfrom

        elif('studies' in request_query):
            _from=request_sfrom
        else:
            _from=request_sgfrom

        page = request.registry.es.search(
            index = request.registry.es_db,
            search_type = 'query_then_fetch',
            from_=_from,
            size=size,
            #from_=#form['from'],
            #size=(form['from']+25),
            body =  {"query" : { "query_string" : {"query" :request_query,"default_operator":"AND",'analyzer': "standard"}}}
        )
        return {'page' : page , 'number': str(page['hits']['total']), 'query' : request_query , 'number_query' :'1'}
    else:
        #return {'ok1111'}
        request_query_dico=form['query_dico']

        projects={}
        studies={}
        signatures={}

        for _type in request_query_dico.keys():
            if("projects" in _type):
                projects[_type]=request_query_dico[_type]
            elif("studies" in _type):
                studies[_type]=request_query_dico[_type]
            elif("signatures" in _type):
                signatures[_type]=request_query_dico[_type]

        if projects != {}:
            projects_keys = projects.keys()
            projects_values = projects.values()
            projects_query= str(projects_keys[0])
            if(len(projects_keys)!=0):
                for index in range(1,len(projects_keys)):
                    projects_query+= ' '+str(projects_values[index])+ ' ' +str(projects_keys[index])
        else:
            projects_query=None


        if studies != {}:
            studies_keys = studies.keys()
            studies_values = studies.values()
            studies_query= str(studies_keys[0])
            if(len(studies_keys)!=0):
                for index in range(1,len(studies_keys)):
                    studies_query+= ' '+str(studies_values[index])+ ' ' +str(studies_keys[index])
        else:
            studies_query=None

        if signatures !={}:
            signatures_keys = signatures.keys()
            signatures_values = signatures.values()
            signatures_query= str(signatures_keys[0])
            if(len(signatures_keys)!=0):
                for index in range(1,len(signatures_keys)):
                    signatures_query+= ' '+str(signatures_values[index])+ ' ' +str(signatures_keys[index])
        else:
            signatures_query=None


        #return{'projects' : projects_query, 'studies' : studies_query, 'signatures': signatures_query}
        #return {'projects':projects_query}
        if projects_query != None:
            project =request.registry.es.search(
                index = request.registry.es_db,
                search_type = 'query_then_fetch',
                from_=request_pfrom,
                size=size,
                #from_=#form['from'],
                #size=(form['from']+25),
                body =  {"query" : { "query_string" : {"query" :projects_query,"default_operator":"AND",'analyzer': "standard"}}}
            )
            number_project=str(project['hits']['total'])
        else:
            project=None
            number_project="0"

        if studies_query !=None:
            study =request.registry.es.search(
                index = request.registry.es_db,
                search_type = 'query_then_fetch',
                from_=request_sfrom,
                size=size,
                #from_=#form['from'],
                #size=(form['from']+25),
                body =  {"query" : { "query_string" : {"query" :studies_query,"default_operator":"AND",'analyzer': "standard"}}}
            )
            number_study=str(study['hits']['total'])
        else:
            study=None
            number_study="0"

        if signatures_query:
            signature =request.registry.es.search(
                index = request.registry.es_db,
                search_type = 'query_then_fetch',
                from_=request_sgfrom,
                size=size,
                #from_=#form['from'],
                #size=(form['from']+25),
                body =  {"query" : { "query_string" : {"query" :signatures_query,"default_operator":"AND",'analyzer': "standard"}}}
            )
            number_signature=str(signature['hits']['total'])
        else:
            signature=None
            number_signature="0"


        return {'projects' : project, 'studies':study , 'signatures' : signature ,'query': request_query, \
                    'number_project' : number_project, 'number_study' : number_study,\
                    'number_signature' :number_signature}

        # query_projects="(_type:projects AND _all:*)"
        # projects = request.registry.es.search(
        #     index = request.registry.es_db,
        #     search_type = 'query_then_fetch',
        #     from_=request_pfrom,
        #     size=25,
        #     #from_=#form['from'],
        #     #size=(form['from']+25),
        #     body =  {"query" : { "query_string" : {"query" :query_projects,"default_operator":"AND",'analyzer': "standard"}}}
        # )

        # query_studies="(_type:studies AND _all:*)"
        # studies = request.registry.es.search(
        #     index = request.registry.es_db,
        #     search_type = 'query_then_fetch',
        #     from_=request_pfrom,
        #     size=25,
        #     #from_=#form['from'],
        #     #size=(form['from']+25),
        #     body =  {"query" : { "query_string" : {"query" :query_studies,"default_operator":"AND",'analyzer': "standard"}}}
        # )

        # query_assays="(_type:assays AND _all:*)"
        # assays = request.registry.es.search(
        #     index = request.registry.es_db,
        #     search_type = 'query_then_fetch',
        #     from_=request_pfrom,
        #     size=25,
        #     #from_=#form['from'],
        #     #size=(form['from']+25),
        #     body =  {"query" : { "query_string" : {"query" :query_assays,"default_operator":"AND",'analyzer': "standard"}}}
        # )


        # query_signatures="(_type:signatures AND _all:*)"
        # signatures = request.registry.es.search(
        #     index = request.registry.es_db,
        #     search_type = 'query_then_fetch',
        #     from_=request_pfrom,
        #     size=25,
        #     #from_=#form['from'],
        #     #size=(form['from']+25),
        #     body =  {"query" : { "query_string" : {"query" :query_signatures,"default_operator":"AND",'analyzer': "standard"}}}
        # )

        # return {'projects' : projects, 'number_projects' : str(projects['hits']['total']),\
        #         'studies' : studies, 'number_studies': str(studies['hits']['total']),\
        #         'assays' : assays, 'number_assays' : str(assays['hits']['total']),\
        #         'signatures' : signatures, 'number_sigbnatures': str(signatures['hits']['total']),\
        #         'query':request_query  }



    # elif request_number_query == 1:

    #     page = request.registry.es.search(
    #         index = request.registry.es_db,
    #         search_type = 'query_then_fetch',
    #         from_=request_pfrom,
    #         size=25,
    #         #from_=#form['from'],
    #         #size=(form['from']+25),
    #         body =  {"query" : { "query_string" : {"query" :request_query,"default_operator":"AND",'analyzer': "standard"}}}
    #     )




    #     return {'page' : page , 'number': str(page['hits']['total']), 'query' : request_query }
    # projects=[]
    # studies=[]
    # assays=[]
    # strategies=[]
    # total=len(page)
    # try:
    #     print("here")
    #     for result in page:
    #         if result['_type'] == 'projects':
    #             projects.append(result)
    #         elif result['_type'] == 'studies':
    #             studies.append(result)
    #         elif result['_type'] == 'assays':
    #             assays.append(result)
    #         else:
    #             strategies.append(result)
    # except:
    #     logger.warning(sys.exc_info())
    # return {'projects':projects,'studies':studies,'assays':assays, 'strategies':strategies, 'len':total}
    # #body = {"query" : { "query_string" : {"query" :request_query,"default_operator":"AND",'analyzer': "standard"}}}
    # return {'projects':projects,'studies':studies,'assays':assays, 'strategies':strategies, 'len':total}




# form = json.loads(request.body, encoding=request.charset)
#     request_query = form['query']
#     if 'from' in form :
#         from_val = form['from']
#     else :
#         from_val = 0

#     page = request.registry.es.search(
#         index = request.registry.es_db,
#         search_type = 'query_then_fetch',
#         from_=0,
#         size=25,
#         #from_=#form['from'],
#         #size=(form['from']+25),
#         body =  {"query" : { "query_string" : {"query" :request_query,"default_operator":"AND",'analyzer': "standard"}}}
#     )
# return page
    #page = request.registry.es.search(
    #index = request.registry.es_db,
    #  search_type = 'query_then_fetch',
    #  size = 100,
    #  from_= from_val,
    #  body = {"query" : { "query_string" : {"query" :request_query,"default_operator":"AND",'analyzer': "standard"}}})

    #return page



@view_config(route_name='user_recover', renderer='json', request_method='POST')
def user_recover(request):
    form = json.loads(request.body, encoding=request.charset)
    if form['user_name'] is None:
        return {'msg': 'Please fill your email first'}
    user_in_db = request.registry.db_mongo['users'].find_one({'id': form['user_name']})
    if user_in_db is None:
        return {'msg': 'User not found'}
    secret = request.registry.settings['secret_passphrase']
    del user_in_db['_id']
    token = jwt.encode({'user': user_in_db,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=36000),
                        'aud': 'urn:chemsign/recover'}, secret)
    message = "You requested a password reset, please click on following link to reset your password:\n"
    message += request.host_url+'/app/index.html#/recover?token='+token
    send_mail(request, form['user_name'], '[ToxSigN] Password reset request', message)
    logging.info(message)
    return {'msg': 'You will receive an email. You must acknowledge it to reset your password.'}


@view_config(route_name='login', renderer='json', request_method='POST')
def login(request):
    form = json.loads(request.body, encoding=request.charset)
    user_in_db = request.registry.db_mongo['users'].find_one({'id': form['user_name']})
    if user_in_db is None:
        return {'msg': 'Invalid email'}

    if bcrypt.hashpw(form['user_password'].encode('utf-8'), user_in_db['password'].encode('utf-8')) == user_in_db['password']:
        secret = request.registry.settings['secret_passphrase']
        del user_in_db['_id']

        token = jwt.encode({'user': user_in_db,
                            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=36000),
                            'aud': 'urn:chemsign/api'}, secret)
        return {'token': token}
    else:
        return {'msg': 'Invalid credentials'}

@view_config(route_name='logged', renderer='json')
def logged(request):
    user = is_authenticated(request)
    if user is None:
        form = json.loads(request.body, encoding=request.charset)
        if form and 'token' in form:
            secret = request.registry.settings['secret_passphrase']
            auth = None
            try:
                auth = jwt.decode(form['token'], secret, audience='urn:chemsign/api')
            except Exception as e:
                return HTTPUnauthorized('Not authorized to access this resource')
            user = {'id': auth['user']['id'], 'token': auth}
            user_in_db = request.registry.db_mongo['users'].find_one({'id': user['id']})
            if user_in_db is None:
                # Create user
                user['status'] = 'pending_approval'
                if user['id'] in request.registry.admin_list:
                    user['status'] = 'approved'
                logging.info('Create new user '+user['id'])
                request.registry.db_mongo['users'].insert({'id': user['id'], 'status': user['status']})
            else:
                user_in_db['token'] = form['token']
                user = user_in_db
        else:
            return HTTPNotFound('Not logged')

    if user is not None and user['id'] in request.registry.admin_list:
        user['admin'] = True

    return user

@view_config(
    context='velruse.AuthenticationComplete',
)
def login_complete_view(request):
    context = request.context
    result = {
        'id': context.profile['verifiedEmail'],
        'provider_type': context.provider_type,
        'provider_name': context.provider_name,
        'profile': context.profile,
        'credentials': context.credentials,
    }
    secret = request.registry.settings['secret_passphrase']
    token = jwt.encode({'user': result,
                        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=36000),
                        'aud': 'urn:chemsign/api'}, secret)
    return HTTPFound(request.static_url('chemsign:webapp/app/')+"index.html#login?token="+token)
