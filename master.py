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
	parser.add_argument('--ip',
			dest='ip', help='IP Address',
			required=True
		)
	return parser


class Master(object):

	def __init__(self, db_name, ip, logging_level=logging.DEBUG):
		self.db = db_name
		self._HEALTH_CHECK_TIME = 0
		self.logger = init_logger(db_name, logging_level)
		self.loc_count = {} # keeps track of search queries and categories in location
		self.cat_count = defaultdict(set) # keeps track of categories whose loc_count >= THRESHOLD_COUNT
		# own IP address
		self.ip = ip

	def SearchForString(self, request, context):
		search_term = request.query
		location = request.location
		print "Location: ", request.location, "\nQuery:", search_term
		loc_count = self.loc_count
		cat_count = self.cat_count
		# increment the values for counts
		replica_list = read_replica_filelist()

		if self.db in ['master', 'backup']:
			if location is not None and len(location) != 0 and location in replica_list:
				if location not in loc_count:
					loc_count[location] = defaultdict(int)
				loc_count[location][search_term] += 1
				
				if loc_count[location][search_term] >= THRESHOLD_COUNT:
					cat_count[location].add(search_term)
					if len(cat_count[location]) >= THRESHOLD_CATEGORIES:
						indices = list(cat_count[location])
						data, indices_to_put = get_data_for_indices(self.db, indices)

						# TODO : CREATE THE REPLICA HERE IF NOT MADE ALREADY
						# TODO : FIND REPLICA IP BY QUERYING
						replica_ip, indices_present = query_metadatadb(self.db, location, indices)

						if replica_ip is None or indices_present == False: # replica needs to be created or updated

							if replica_ip is None: # replica not present already

								# Assume we have one replica server per location
								# TODO: remove break so that we consider multiple servers
								for replica in replica_list[location]:
									self.logger.info("Setting up the replica in "+location+ " at "+ replica)
									print "Setting up the replica in "+ location + " at " + replica
									replica_ip = replica

									channel = grpc.insecure_channel(replica_ip)
									stub = search_pb2_grpc.ReplicaCreationStub(channel)
									request = search_pb2.ReplicaRequest(data = data, master_ip = self.ip, create = True)
									# TODO: add this entry to the metadata table
									add_to_metadatadb(self.db, replica_ip, location, indices_to_put)

							elif replica_ip is not None and indices_present == False: # replica present but indices not present
								self.logger.info("Adding indices to the replica in "+location+ " at "+ replica_ip)
								print "Adding indices " + str(indices_to_put) + "to the replica in "+ location + " at " + replica_ip
								channel = grpc.insecure_channel(replica_ip)
								stub = search_pb2_grpc.ReplicaCreationStub(channel)
								request = search_pb2.ReplicaRequest(data = data, master_ip = self.ip, create = False)
								# TODO: update the entry in the metadata table

							# create or update the replica
							try :
								print "Querying the replica"
								response = stub.CreateReplica(request, timeout = 10)
								print(response)
							except Exception as e:
								print str(e)
								if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
									print("DEADLINE_EXCEEDED!\n")
									self.logger.error("Deadline exceed - timeout before response received")
								if str(e.code()) == "StatusCode.UNAVAILABLE":
									print("UNAVAILABLE!\n")
									self.logger.error("Master server unavailable")

						else: # replica present with indices
							self.logger.debug("Received query: " + search_term, "redirecting to replica " + replica_ip + " at " + location)

						#now query replica's db for urls
						channel = grpc.insecure_channel(replica_ip)
						stub = search_pb2_grpc.SearchStub(channel)
						request = search_pb2.SearchRequest(query = search_term)
						try:
							response = stub.SearchForString(request)
						except Exception as e:
							print str(e)
							self.logger.error("Replica could not be contacted, falling back to master")
							urls = querydb(self.db, search_term)
							print urls
							return search_pb2.SearchResponse(urls=urls)

						return search_pb2.SearchResponse(urls=response.urls)

		urls = querydb(self.db, search_term)
		
		self.logger.debug("Received query: " + search_term)
		print urls
		return search_pb2.SearchResponse(urls=urls)

	def Check(self, request, context):
		self.logger.debug("Received heartbeat query from backup")
		self._HEALTH_CHECK_TIME += 1
		return search_pb2.HealthCheckResponse(status = "STATUS: Master server up!")

	def CreateReplica(self, request, context):
		# replica on receiving set up request
		data = json_util.loads(request.data)
		master_ip = request.master_ip
		print "Request for creating replica"
		print "adding the data"
		addtodb(self.db, data)
		return search_pb2.ReplicaStatus(status=1)


def serve(db_name, ip, logging_level=logging.DEBUG, port='50051'):
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	master = Master(db_name, ip, logging_level)
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
	ip = options.ip
	print ip
	level = options.logging_level
	logging_level = parse_level(level)
	serve('master', ip, logging_level)


if __name__ == '__main__':
	main()
