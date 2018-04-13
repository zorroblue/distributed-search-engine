from concurrent import futures
import time
import math
import json

from argparse import ArgumentParser
import argparse

import grpc
import search_pb2
import search_pb2_grpc

import logging
from utils import querydb, init_logger, parse_level, addtodb, createdb

from writeservice import WriteService

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

THRESHOLD_COUNT = 1
THRESHOLD_CATEGORIES = 1

def build_parser():
	parser = ArgumentParser()
	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	return parser


class Master(object):

	def __init__(self, db_name, logging_level=logging.DEBUG):
		self.db = db_name
		self._HEALTH_CHECK_TIME = 0
		self.logger = init_logger(db_name, logging_level)
		self.loc_count = {} # keeps track of search queries and categories in location
		self.cat_count = {} # keeps track of number of categories whose loc_count > THRESHOLD_COUNT

	def SearchForString(self, request, context):
		search_term = request.query
		location = request.location
		
		# increment the values for counts
		if location is not None:
			if location not in loc_count:
				loc_count[location] = defaultdict(int)
			loc_count[location][search_term] += 1
			if loc_count[location][search_term] == THRESHOLD_COUNT and location not in cat_count:
				cat_count[location] = 1
				if len(cat_count.keys()) == THRESHOLD_CATEGORIES:
					# TODO : CREATE THE REPLICA HERE
					# TODO : FIND REPLICA IP BY QUERYING
					pass

		urls = querydb(self.db, search_term)
		
		self.logger.debug("Received query: " + search_term)
		print urls
		return search_pb2.SearchResponse(urls=urls)

	def Check(self, request, context):
		self.logger.debug("Received heartbeat query from backup")
		self._HEALTH_CHECK_TIME += 1
		return search_pb2.HealthCheckResponse(status = "STATUS: Master server up!")


def serve(db_name, logging_level=logging.DEBUG, port='50051'):
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	master = Master(db_name, logging_level)
	search_pb2_grpc.add_SearchServicer_to_server(master, server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(master, server)
	write_service = WriteService(db_name, logger=master.logger)
	search_pb2_grpc.add_DatabaseWriteServicer_to_server(write_service, server)
	server.add_insecure_port('[::]:'+ port)
	server.start()
	master.logger.info("Starting server")
	print "Starting master"
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		master.logger.info("Shutting down server")
		logging.shutdown()
		server.stop(0)


def main():
	parser = build_parser()
	options = parser.parse_args()
	level = options.logging_level
	logging_level = parse_level(level)
	serve('master', logging_level)


if __name__ == '__main__':
	main()
