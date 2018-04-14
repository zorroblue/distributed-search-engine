'''
Utility functions
'''

import pprint
import json
from pymongo import MongoClient
import logging

import argparse
from argparse import ArgumentParser
from bson import json_util
from bson import BSON


# TODO : add time of creation/update
# Metadata db
def add_to_metadatadb(sender, replica_ip, location, indices):
	record = {}
	record["replica_ip"] = replica_ip
	record["location"] = location
	record["indices"] = indices

	client = MongoClient('localhost', 27017)
	db = client[sender+'_metadatadb']
	metadata_coll = db.metadata
	metadata_coll.insert(json.loads(json.dumps([record])))
	print "Success"


def query_metadatadb(sender, location, search_term):
	client = MongoClient('localhost', 27017)

	db = client[sender+'_metadatadb']
	metadata_coll = db.metadata
	responses = metadata_coll.find({"location":location})
	for response in responses:

		if search_term in response["indices"]:
			print response["indices"]
			print search_term+ " found in "+ response["replica_ip"]
			return response["replica_ip"]
	return None


def get_similar(sender, words):
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb

	indices = db.indices
	responses = indices.find({"status" : "committed", "name" :{"$in": words}})
	client.close()

	similar = set()
	if responses is not None:
		for response in responses:
			similar.update(response["sim_words"])
		
	return list(similar)

def get_data_for_indices(sender, indices):
	indices = get_similar(indices)

	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb
	indices_coll = db.indices
	responses = indices_coll.find({"status" : "committed", "name" :{"$in": indices}})
	result =  json_util.dumps(responses, sort_keys=True, indent=4, default=json_util.default)
	return result




def querydb(sender, search_term):
	'''Query on mongodb database for suitable response for search term
	'''
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb

	indices = db.indices
	response = indices.find_one({"status" : "committed", "name" : search_term})
	client.close()
	if response is not None:
		return response["urls"]
	return []

def addtodb(sender, indices):
	'''Add json string to db
	'''
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb

	print "Adding to DB"
	data = json.loads(indices.decode('string-escape').strip('"'))
	indices = db.indices
	result = indices.insert_many(data)
	print "Added ", len(result.inserted_ids)
	print indices.count()
	client.close()
	return True


def commitdb(sender):
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb
	print "COMMIT"
	indices = db.indices

	# remove duplicate records whose status is committed and who have names in the pending list
	words = indices.find({"status" : "pending"}, {"name" : 1, '_id' : 0})
	words = [x['name'] for x in words]
	print "Duplicates : ",words
	status = indices.remove({"status" : "committed", "name" :{"$in": words}})
	print status
	
	# update pending records to committed
	status = indices.update({'status': 'pending'},
          {'$set': {'status':'committed'}}, 
          multi=True)
	print "Write status ", status
	print "Total length of documents ", indices.count()
	client.close()


def rollbackdb(sender):
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb
	print "ROLLBACK"
	indices = db.indices
	status = indices.delete_many({'status' : 'pending'})
	print status
	client.close()


def init_logger(db_name, logging_level):
	logger = logging.getLogger(db_name)
	logger.setLevel(logging_level)
	# add handler only if already added
	if not len(logger.handlers):
		fh = logging.FileHandler('log'+db_name+'.log')
		fh.setLevel(logging_level)
		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fh.setFormatter(formatter)
		logger.addHandler(fh)
	return logger


def parse_level(level):
	if level == 'DEBUG':
		logging_level = logging.DEBUG
	elif level == 'INFO':
		logging_level = logging.INFO
	elif level == 'WARNING':
		logging_level = logging.WARNING
	elif level == 'ERROR':
		logging_level = logging.ERROR
	elif level == 'CRITICAL':
		logging_level = logging.CRITICAL
	else:
		message = 'Invalid choice! Please choose from DEBUG, INFO, WARNING, ERROR, CRITICAL'
		argparse.ArgumentError(self, message)
	return logging_level

def read_replica_filelist():
	f = open("replicas_list.txt")
	replica_ips = {}
	for line in f:
		line = line.strip().split()
		# IP LOCATION
		location = line[1].strip()
		ip = line[0].strip()
		if location not in replica_ips:
			replica_ips[location] = []
		replica_ips[location].append(ip)
	print replica_ips
	return replica_ips

