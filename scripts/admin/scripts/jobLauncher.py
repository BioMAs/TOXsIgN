'''
Created on 21 mars. 2017

@author: tdarde
'''
from pymongo import MongoClient
import ConfigParser, os
import argparse
from time import *
import datetime
import subprocess



print os.getcwd() 

config = ConfigParser.ConfigParser()
config.readfp(open(os.path.join(os.getcwd(),'var/upload/admin/scripts/config.ini')))

mongo = MongoClient(config.get('app:main','db_uri'))
db = mongo[config.get('app:main','db_name')]


def run_dist(signature_id,job_id,user_id):
	log = ""
	signature = db['signatures'].find_one({'id': signature_id})
	db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'pending'}})
	print "Create tmp dir"
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':'Create tmp dir\n'}})
	log = log + 'Create tmp dir\n'
	dt = datetime.datetime.utcnow()
	ztime = mktime(dt.timetuple())

	name_dir = "TSJ"+str(job_id)+"_"+str(ztime)
	tmp_dir = os.path.join(os.getcwd(),'var/upload/admin/tmp_jobs',name_dir)
	
	
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)
	
	if not os.path.exists(os.path.join(os.getcwd(),'var/jobs/',name_dir)):
		os.makedirs(os.path.join(os.getcwd(),'var/jobs/',name_dir))
	else :
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'error'}})
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':'Job path already exists.'}})
		return 1

	if user_id == 'None':
		print "Create Signatures file for None user"
		log = log + 'Create Signatures\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		signature = db['signatures'].find_one( { '$and': [{ 'id': signature_id }, { 'status': 'public' }, { 'type': 'Genomic' } ] } )
		check_files = open(tmp_dir+'/'+signature['id']+'.sign','a')
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
			fileAdmin.close()
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
			fileAdmin.close()
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
			fileAdmin.close()


		log = log + 'Copy files\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd_cp = "cp %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/public.RData'),tmp_dir)
		os.system(cmd_cp)
		cmd_mv = "mv %s %s" % (os.path.join(tmp_dir,'public.RData'),os.path.join(tmp_dir,'signature_matrix.RData'))
		os.system(cmd_mv)
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'running'}})
		print 'Create R  matrix'

	if user_id != 'None':
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'running'}})
		print "Create Signatures file for None user"
		all_signature_private = []
		all_signature_private.extend(list(db['signatures'].find( { '$and': [ { 'type': 'Genomic' }, { 'owner': user_id }] } )))
		all_signature_private.append(db['signatures'].find_one( { '$and': [{ 'id': signature_id }, { 'status': 'public' }, { 'type': 'Genomic' } ] } ))
		log = log + 'Copy files\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd_cp = "cp %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/public.RData'),tmp_dir)
		os.system(cmd_cp)

		print "Create all sign files"
		for signature in all_signature_private :
			check_files = open(tmp_dir+'/'+signature['id']+'.sign','a')
			if signature['status'] == 'private':
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()


			if signature['status'] == 'pending approval':
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()
	
			if signature['status'] == 'public':
				print os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'])
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()
			check_files.close()

		print 'Create R matrix'
		log = log + 'Create R matrix\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd7 = "Rscript %s %s %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/create_signmatrix4distance.R'),tmp_dir,os.path.join(tmp_dir,'public.RData'),os.path.join(tmp_dir,'signature_matrix.RData'))
		print cmd7
		os.system(cmd7)
		print 'Create R  matrix DONE'
		print "Create all sign files - DONE"
	
	
	#For everyone
	print "Run script enrich"
	log = log + 'Run script enrich\n'
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
	cmd8 = "Rscript %s %s %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/distance4signatures.R'),os.path.join(tmp_dir,signature_id+'.sign'),os.path.join(tmp_dir,'signature_matrix.RData'),os.path.join(os.getcwd(),'/var/jobs/',name_dir))
	print cmd8
	os.system(cmd8)
	print "Calcul distance Done"
	log = log + 'Calcul distance Done\n'
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
	cmdcp = "cp %s %s" % (os.path.join(tmp_dir,signature_id+'.sign.dist'),os.path.join(os.getcwd(),'var/jobs/',name_dir))
	os.system(cmdcp)
	cmd9 = "rm -rf %s" % (tmp_dir)
	#os.system(cmd9)
	db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'success'}})
	db['Jobs'].update({'id': int(job_id)},{'$set':{'result':os.path.join(os.getcwd(),'var/jobs/',name_dir,signature_id+'.sign.dist')}})


def run_enrich(signature_id,job_id,user_id):
	log = ""
	signature = db['signatures'].find_one({'id': signature_id})
	db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'pending'}})
	print "Create tmp dir"
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':'Create tmp dir\n'}})
	log = log + 'Create tmp dir\n'
	dt = datetime.datetime.utcnow()
	ztime = mktime(dt.timetuple())

	name_dir = "TSJ"+str(job_id)+"_"+str(ztime)
	tmp_dir = os.path.join(os.getcwd(),'var/upload/admin/tmp_jobs',name_dir)
	
	
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)
	
	if not os.path.exists(os.path.join(os.getcwd(),'var/jobs/',name_dir)):
		os.makedirs(os.path.join(os.getcwd(),'var/jobs/',name_dir))
	else :
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'error'}})
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':'Job path already exists.'}})
		return 1

	if user_id == 'None':
		print "Create Signatures file for None user"
		log = log + 'Create Signatures\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		signature = db['signatures'].find_one( { '$and': [{ 'id': signature_id }, { 'status': 'public' }, { 'type': 'Genomic' } ] } )
		check_files = open(tmp_dir+'/'+signature['id']+'.sign','a')
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
			fileAdmin.close()
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
			fileAdmin.close()
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
			for linesFile in fileAdmin.readlines():
				check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
			fileAdmin.close()


		log = log + 'Copy files\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd_cp = "cp %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/public.RData'),tmp_dir)
		os.system(cmd_cp)
		cmd_mv = "mv %s %s" % (os.path.join(tmp_dir,'public.RData'),os.path.join(tmp_dir,'signature_matrix.RData'))
		os.system(cmd_mv)
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'running'}})
		print 'Create R  matrix'

	if user_id != 'None':
		db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'running'}})
		print "Create Signatures file for None user"
		all_signature_private = []
		all_signature_private.append(db['signatures'].find_one( { '$and': [{ 'id': signature_id }, { 'type': 'Genomic' } ] } ))
		log = log + 'Copy files\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd_cp = "cp %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/public.RData'),tmp_dir)
		os.system(cmd_cp)

		print "Create all sign files"
		for signature in all_signature_private :
			check_files = open(tmp_dir+'/'+signature['id']+'.sign','a')
			if signature['status'] == 'private':
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()


			if signature['status'] == 'pending approval':
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/upload/'+user_id+'/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()
	
			if signature['status'] == 'public':
				print os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'])
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
					fileAdmin.close()
				if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down']):
					fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
					for linesFile in fileAdmin.readlines():
						check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
					fileAdmin.close()
			check_files.close()

		print 'Create R matrix'
		log = log + 'Create R matrix\n'
		db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
		cmd7 = "Rscript %s %s %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/create_signmatrix4distance.R'),tmp_dir,os.path.join(tmp_dir,'public.RData'),os.path.join(tmp_dir,'signature_matrix.RData'))
		print cmd7
		os.system(cmd7)
		print 'Create R  matrix DONE'
		print "Create all sign files - DONE"
	
	
	#For everyone
	print "Run script enrich"
	log = log + 'Run prepare_enrichment\n'
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
	cmd8 = "wish8.6 %s -hg2go %s -sign %s -o %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/prepare_enrichment.tcl'),os.path.join(os.getcwd(),'var/upload/admin/annotation/annotation'),os.path.join(tmp_dir,signature_id+'.sign'),os.path.join(tmp_dir,signature_id+'.enr'))
	print cmd8
	os.system(cmd8)
	log = log + 'Run enrichment\n'
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})
	cmd9 = "Rscript %s %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/compute_enrichment.R'),os.path.join(tmp_dir,signature_id+'.enr'),os.path.join(tmp_dir,signature_id+'.enr'))
	print cmd9
	os.system(cmd9)
	print "Calcul distance Done"
	log = log + 'Calcul distance Done\n'
	db['Jobs'].update({'id': int(job_id)},{'$set':{'stderr':log}})


	cmdcp = "cp %s %s" % (os.path.join(tmp_dir,signature_id+'.enr'),os.path.join(os.getcwd(),'var/jobs/',name_dir))
	os.system(cmdcp)
	cmd9 = "rm -rf %s" % (tmp_dir)
	#os.system(cmd9)
	db['Jobs'].update({'id': int(job_id)},{'$set':{'status':'success'}})
	db['Jobs'].update({'id': int(job_id)},{'$set':{'result':os.path.join(os.getcwd(),'var/jobs/',name_dir,signature_id+'.enr')}})


def create_RData():

	print "Create Signatures file for None user"
	all_signature = list(db['signatures'].find( { '$and': [ { 'status': 'public' }, { 'type': 'Genomic' }] } ))
	tmp_dir = os.path.join(os.getcwd(),'var/upload/admin/publicFiles/')
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)
	print "Create all sign files"
	for signature in all_signature :
		dSign={}
		check_files = open(tmp_dir+'/'+signature['id']+'.sign','a')
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_up'],'r')
			for linesFile in fileAdmin.readlines():
				dSign[linesFile.split('\t')[0]] =""
				check_files.write(linesFile.replace('\n','')+'\t'+str(1)+'\n')
			fileAdmin.close()
		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_down'],'r')
			for linesFile in fileAdmin.readlines():
				dSign[linesFile.split('\t')[0]] =""
				check_files.write(linesFile.replace('\n','')+'\t'+'-1'+'\n')
			fileAdmin.close()

		if os.path.isfile(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated']):
			fileAdmin = open(os.getcwd()+'/var/Data/Public/'+signature['projects']+'/'+signature['id']+'/'+signature['file_interrogated'],'r')
			for linesFile in fileAdmin.readlines():
				if linesFile.split('\t')[0] not in dSign:
					check_files.write(linesFile.replace('\n','')+'\t'+str(0)+'\n')
			fileAdmin.close()

		
				
		check_files.close()
	print "Create all sign files - DONE"
	
	print 'Create R  matrix'
	cmd7 = "Rscript %s %s %s %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/create_signmatrix4distance.R'),tmp_dir,"tmp_matrix",os.path.join(os.getcwd(),'var/upload/admin/scripts/public.RData'))
	print cmd7
	os.system(cmd7)
	cmdrm = "rm -rf %s" % (tmp_dir)
	os.system(cmdrm)
	print 'Create R  matrix DONE'


def create_homologene():
	tmp_dir = os.path.join(os.getcwd(),'var/upload/admin/annotation/')
	if not os.path.exists(tmp_dir):
		os.makedirs(tmp_dir)

	print "create annotation files"
	cmd1 = "wish8.6 %s -hg %s -gene2go %s -goobo %s -o %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/homologene2go.tcl'),os.path.join(os.getcwd(),'var/upload/admin/annotation/homologene.data'),os.path.join(os.getcwd(),'var/upload/admin/annotation/gene2go'),os.path.join(os.getcwd(),'var/upload/admin/annotation/gene_ontology.obo'),tmp_dir)
	cmd2 = "wish8.6 %s -hg %s -gene2hpo %s -hpoobo %s -o %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/homologene2hpo.tcl'),os.path.join(os.getcwd(),'var/upload/admin/annotation/homologene.data'),os.path.join(os.getcwd(),'var/upload/admin/annotation/ALL_SOURCES_ALL_FREQUENCIES_genes_to_phenotype.txt'),os.path.join(os.getcwd(),'var/upload/admin/annotation/hp.obo'),tmp_dir)
	cmd3 = "wish8.6 %s -hg %s -gene2mgi %s -mgi2mpo %s -mpoobo %s -o %s" % (os.path.join(os.getcwd(),'var/upload/admin/scripts/homologene2mpo.tcl'),os.path.join(os.getcwd(),'var/upload/admin/annotation/homologene.data'),os.path.join(os.getcwd(),'var/upload/admin/annotation/MGI_Gene_Model_Coord.rpt'),os.path.join(os.getcwd(),'var/upload/admin/annotation/MGI_PhenoGenoMP.rpt'),os.path.join(os.getcwd(),'var/upload/admin/annotation/MPheno_OBO.ontology'),tmp_dir)
	print "HOMOLOGENE START"
	os.system(cmd1)
	print "HOMOLOGENE DONE"
	
	print "HPO START"
	os.system(cmd2)
	print "HPO DONE"
	
	print "MPI START"
	os.system(cmd3)
	print "MPI DONE"
	print "Annotation file done"
	if os.path.isfile(os.path.join(tmp_dir,'annotation')) :
		os.remove(os.path.join(tmp_dir,'annotation'))
	cmd4 = "cat %s/homologene2go >> %s/annotation" % (tmp_dir,tmp_dir)
	cmd5 = "cat %s/homologene2mpo >> %s/annotation" % (tmp_dir,tmp_dir)
	cmd6 = "cat %s/homologene2hpo >> %s/annotation" % (tmp_dir,tmp_dir)
	os.system(cmd4)
	os.system(cmd5)
	os.system(cmd6)
	
    





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize database content.')
    parser.add_argument('--signature')
    parser.add_argument('--script')
    parser.add_argument('--job')
    parser.add_argument('--user')
    args = parser.parse_args()

    if args.script == 'distance_analysis':
		run_dist(args.signature,args.job,args.user)
    if args.script == 'functional_analysis':
        run_enrich(args.signature,args.job,args.user)
    if args.script == 'gopublic':
		create_RData()
    if args.script == 'gohomo':
		create_homologene()
