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
Last Update : 30/11/2016
"""

#lTaxID=[9606,9598,9544,9615,9913,10090,10116,9031,8364,7955,7227,7165,6239,4932,28985,33169,4896,318829,5141,3702,4530]
#geneFile = open('gene_info','r')
#geneFileOut = open('gene_info_parse','a')
#for geneLine in geneFile.readlines():
#    if geneLine[0] != '#':
#        tax_id = geneLine.split('\t')[0]
#        if int(tax_id) in lTaxID :
 #           geneFileOut.write(geneLine)
            



def CreateFileDB(fileGene,fileHomo):
    homoFile = open(fileHomo,'r')
    dHomo = {}
    for homoline in homoFile.readlines():
        HID = homoline.split('\t')[0]
        Taxonomy_ID = homoline.split('\t')[1]
        Gene_ID = homoline.split('\t')[2]
        Gene_Symbol = homoline.split('\t')[3]
        Protein_gi = homoline.split('\t')[4]
        Protein_accession = homoline.split('\t')[5]
        if Gene_ID not in dHomo:
            dHomo[Gene_ID] = HID
        else :
            print 'double'
    homoFile.close()
    geneFile = open(fileGene,'r')
    geneFileOut = open('TOXsIgN_geneDB','a')
    dGene = {}
    for geneLine in geneFile.readlines():
        tax_id = geneLine.split('\t')[0]
        GeneID = geneLine.split('\t')[1]
        Symbol = geneLine.split('\t')[2] 
        Synonyms = geneLine.split('\t')[4] 
        description = geneLine.split('\t')[8]
        if GeneID in dHomo :
            geneFileOut.write(geneLine.replace('\n','')+'\t'+dHomo[GeneID]+'\n')
        else :
            geneFileOut.write(geneLine.replace('\n','')+'\tNA\n')
    
    geneFileOut.close()
CreateFileDB('../../Data/Database/gene_info_parse', '../../Data/Database/homologene.data.txt')
        