'''
Utility functions
'''

import pprint
import json
from pymongo import MongoClient

def querydb(sender, search_term):
	'''Query on mongodb database for suitable response for search term
	'''
	client = MongoClient('localhost', 27017)
	if sender == 'master':
		db = client.masterdb
	else:
		db = client.replicadb

	indices = db.indices
	response = indices.find_one({"name" : search_term})
	client.close()
	if response is not None:
		return response["urls"]
	return []
