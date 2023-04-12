from pymongo import MongoClient
import os, csv,sys
sys.path.append('config')
from config import config
from connect import connect
# Author: Diego Fernando Rodriguez
# Date: 29/11/2020

# Script para generar csv con parametros biofisicos segun la macroregion con los parametros por defecto o ingresados por determinado usuario


def connectMongo(host,port):
    connection = MongoClient(host,port)
    return connection

# Obtener parametros biofisicos por defecto filtrados por
# macroregion 

def getDefaultBiophysicParams(macro_region,default):
    results = list()
    keys=list()
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('get_default_biophysycal_params', [macro_region,default])
    result = cursor.fetchall()
    resultKeys=cursor.description
    for key in resultKeys:
        # print("RESULT KEY")
        # print(key[0])
        keys.append(key[0])
    for row in result:
        # print("Row")
        # print(row)
        results.append(row)
    return results,keys

# Obtener parametros biofisicos por defecto filtrados por
# macroregion 

def getUserBiophysicParams(intake,studyCase,user,macro_region,default):
    results = list()
    keys=list()
    cursor = connect('postgresql_alfa').cursor()
    cursor.callproc('get_user_biophysycal_params', [macro_region,default,intake,studyCase,user])
    result = cursor.fetchall()
    resultKeys=cursor.description
    for key in resultKeys:
        # print("RESULT KEY")
        # print(key[0])
        keys.append(key[0])
    for row in result:
        # print("Row")
        # print(row)
        results.append(row)
    return results,keys

def getColsParams(host,port,database,collection,user,macro_region,default):
    con = connectMongo(host,port)
    db = con[database]
    col = db[collection]
    query = { "user": str(user), "macro_region": str(macro_region) }
    results = list()

    doc = col.find(query)
    countUser = doc.count()
    keys = None

    if countUser == 0:
        queryCol = {"macro_region": str(macro_region), "default":"y"}
        docs = col.find(queryCol)
        first = docs[0]
        keys = list(first.keys())
        for x in docs:
            #print(x)
            results.append(list(x.values()))
    elif countUser > 0:
        print("::MAS DE UN USUARIO:::")
        queryCol = {"macro_region": str(macro_region), "default":"n","user": str(user)}
        queryColDef = {"macro_region": str(macro_region), "default":"y"}
        docs = col.find(queryCol)
        docsD = col.find(queryColDef)
        first = docsD[0]
        keys = list(first.keys())
        lucodes = list()
        for x in docs:
            results.append(list(x.values()))
            lucodes.append(x["lucode"])
        
        for y in docsD:
            for lu in lucodes:
                if y['lucode'] != lu:
                    results.append(list(y.values()))
    
    con.close()
    print("KEYS")
    print(keys)
    return results, keys

def generateCsv(header,values, file):
    row_list = []
    row_list.append(header)

    for item in values:
        row_list.append(item)
	
    with open(file,"w") as file:
        writer = csv.writer(file)
        writer.writerows(row_list)

def readCsv(file,field):

    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        index = 0
        resultList = []
        for row in csv_reader:
            if line_count == 0:
                # print("Name: " + row)
                if field in row:
                    index = row.index(field)
                line_count += 1
            else:
                # print("Value: " + row)
                resultList.append(row[index])
                line_count += 1

    return resultList

def filterCsvLucode(file,field):
    with open(file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        index = 0
        resultList = []
        for row in csv_reader:
            if line_count == 0:
                # print("Name: " + row)
                if field in row:
                    index = row.index(field)
                line_count += 1
            else:
                # print("Value: " + row)
                if (int(row[index])<=8):
                    resultList.append(row[index])
                line_count += 1

    return resultList
# connectMongo("apps.skaphe.com",27017,"waterProof","parametros_biofisicos")

# values,headers = getColsParams("apps.skaphe.com",27017,"waterProof","parametros_biofisicos",1,"SA_1",True)
# generateCsv(headers,values)

