'''
Utility functions
'''

import pprint
import json
from pymongo import MongoClient
import logging

import argparse
from argparse import ArgumentParser


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


def init_logger(db_name, logging_level):
	logger = logging.getLogger(db_name)
	logger.setLevel(logging_level)
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