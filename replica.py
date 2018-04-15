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
from utils import *

from writeservice import WriteService
from collections import defaultdict

from master import Master

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

THRESHOLD_COUNT = 1
THRESHOLD_CATEGORIES = 1

def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--port',
			dest='port', help='Port',
			required=True)

	parser.add_argument('--ip',
			dest='ip', help='IP Address',
			required=True)

	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	parser.add_argument('--name',
			dest='name', help='Replica name',
			required=True)
	return parser

# def UpdateReplica(self, request, context):
# 	self.logger.debug("Received Update Request from master")
# 	self.logger.debug(request.data, request.master_ip)
# 	return search_pb2.ReplicaStatus(status = 1)

def run(name, ip, port, logging_level):
	logger = init_logger(name, logging_level)
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	# add write service to replica to handle database updates from master 
	write_service = WriteService(name, logger=logger)
	search_pb2_grpc.add_DatabaseWriteServicer_to_server(write_service, server)
	write_service = WriteService(name, logger=logger)
	search_pb2_grpc.add_DatabaseWriteServicer_to_server(write_service, server)
	
	# the dynamic replica need to query the backup hence doesn't need to know who the backup is
	master = Master(name, ip, None, logging_level)
	search_pb2_grpc.add_SearchServicer_to_server(master, server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(master, server)
	search_pb2_grpc.add_ReplicaUpdateServicer_to_server(master, server)
	search_pb2_grpc.add_ReplicaCreationServicer_to_server(master, server)
	print("Starting replica "+name)
	server.add_insecure_port('[::]:'+ port)
	server.start()
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
	name = options.name
	ip = options.ip
	port = options.port
	logging_level = parse_level(options.logging_level)
	run(name, ip, port, logging_level)

if __name__ == '__main__':
	main()