from concurrent import futures
import time
import math
import json
import thread

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
MAX_RETRIES = 3
THRESHOLD_CATEGORIES = 1
THRESHOLD_IDLETIME = 120

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

	parser.add_argument('--backup',
			dest='backup', help='Backup IP Address',
			required=True
		)
	return parser


class Master(object):


	def __init__(self, db_name, ip, backup, logging_level):
		self.db = db_name
		self.backup = backup
		self._HEALTH_CHECK_TIME = 0
		self.logger = init_logger(db_name, logging_level)
		self.loc_count = {} # keeps track of search queries and categories in location
		self.cat_count = defaultdict(set) # keeps track of categories whose loc_count >= THRESHOLD_COUNT
		# own IP address
		self.ip = ip
		self.master_backup_ip = master_backup_ip

		if db_name not in ['master', 'backup']:
			self.wordIdletimes = {} #keeps track of the time for which a word has not been queried from a replica

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

						replica_ip, indices_present = query_metadatadb(self.db, location, indices)
						print "Queried metadata", indices_present, replica_ip

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
									break

							elif replica_ip is not None and indices_present == False: # replica present but indices not present
								self.logger.info("Adding indices to the replica in "+location+ " at "+ replica_ip)
								print "Adding indices " + str(indices_to_put) + "to the replica in "+ location + " at " + replica_ip
								channel = grpc.insecure_channel(replica_ip)
								stub = search_pb2_grpc.ReplicaCreationStub(channel)
								request = search_pb2.ReplicaRequest(data = data, master_ip = self.ip, create = False)

							# create or update the replica
							try :
								print "Querying the replica"
								response = stub.CreateReplica(request, timeout = 10)
								print(response)
								# Add this entry to the metadata table
								# initiate 2 phase commit for the same
								if self.db == 'master':
									# 2 Phase commit for sequential consistency with backup
									self.initiate_2_phase_commit(replica_ip, location, indices_to_put)
								else: # backup
									# don't do anything since master has crashed
									add_to_metadatadb(self.db, replica_ip, location, indices_to_put)
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
		if len(urls)>0 and self.db not in ['master', 'backup']:
			self.wordIdletimes[search_term] = 0
		self.logger.debug("Received query: " + search_term)
		print urls
		return search_pb2.SearchResponse(urls=urls)


	def initiate_2_phase_commit(self, replica_ip, location, indices_to_put):
		print "Starting two phase commit"
		logger = self.logger
		logger.info("Starting 2 phase commit")
		print "Phase 1: Prepare"
		backup = self.backup
		print "Backup is", backup
		backup_channel = grpc.insecure_channel(backup)
		backup_stub = search_pb2_grpc.DatabaseWriteStub(backup_channel)
		backup_vote = None
		try:
			logger.info("Send COMMIT_REQUEST to backup")
			request = search_pb2.CommitRequest(replica_ip=replica_ip, location=location, indices=indices_to_put)
			backup_vote = backup_stub.QueryToCommit(request)
			print "Backup Status: ", backup_vote.status
			if backup_vote.status == 1:
				logger.info("Received AGREED from backup")
			else:
				logger.info("Received ABORT from backup")
		except Exception as e:
			print str(e)
			print e.code()
			logger.error("Backup not reachable due to "+ str(e.code()))
	
		logger.info("Added "+replica_ip+", "+location+", "+str(indices_to_put))
		add_to_metadatadb(self.db, replica_ip, location, indices_to_put)
		
		backup_ack = None
		if backup_vote is not None:
			if backup_vote.status == 1:
				logger.info("Transaction COMMIT")
				logger.info("Sending COMMIT to backup")
				request = search_pb2.CommitStatusUpdate(code=search_pb2.COMMIT)
				retries = 0
				while retries < MAX_RETRIES:
					try:
						backup_ack = backup_stub.CommitPhase(request)
						retries = MAX_RETRIES
						if backup_ack.status == 1:
							logger.info("Backup ACK received")
							logger.info("transaction complete")
					except Exception as e:
						if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
							print("DEADLINE_EXCEEDED!\n")
							logger.error("Deadline exceed - timeout before response received")
						if str(e.code()) == "StatusCode.UNAVAILABLE":
							print("UNAVAILABLE!\n")
							logger.error("Backup server unavailable")



	def Check(self, request, context):

		if(self.db == 'master'):
			self.logger.debug("Received heartbeat query from backup")
			self._HEALTH_CHECK_TIME += 1
			return search_pb2.HealthCheckResponse(status = "STATUS: Master server up!")

		# else it is a replica getting health check message from master
		self.logger.debug("Received heartbeat query from master")

		allwords = getallwords(self.db)
		print "ALL WORDS IN DB:" + str(allwords)
		print "wordIdletimes: " + str(self.wordIdletimes)
		for word in allwords:
			if word not in self.wordIdletimes.keys():
				self.wordIdletimes[word] = 0

		for word in self.wordIdletimes.keys():
			if word not in allwords:
				self.wordIdletimes.pop(word, None)

		indices_to_remove = ""
		words_to_remove = []
		for word in self.wordIdletimes.keys():
			self.wordIdletimes[word] += 1
			if(self.wordIdletimes[word] == THRESHOLD_IDLETIME):

				self.wordIdletimes.pop(word, None)
				indices_to_remove += " " + word
				words_to_remove.append(word)


		removefromdb(self.db, words_to_remove)
		print "IDLE WORDS: " + indices_to_remove

		return search_pb2.HealthCheckResponse(status = "Replica" + self.ip + " up!", data = indices_to_remove)


	def UpdateReplica(self, request, context):
		self.logger.debug("Received Update Request from master " + request.master_ip)
		print request.data
		if update_db(self.db, request.data):
			self.logger.debug(self.db + "db successfully updated")
			return search_pb2.ReplicaStatus(status = 1)
		else:
			self.logger.debug("Error in updating " + self.db + "db")
			return search_pb2.ReplicaStatus(status = 0)




	def CreateReplica(self, request, context):
		# replica on receiving set up request
		data = json_util.loads(request.data)
		master_ip = request.master_ip
		print "Request for creating replica"
		print "adding the data"
		addtodb(self.db, data)
		return search_pb2.ReplicaStatus(status=1)


def updateReplicaAndBackup(master):
	while True:
		time.sleep(10)
		# Replica
		replica_ips = get_all_replica_ips(master.db)
		for replica_ip in replica_ips:
			data, indices_to_put = get_data_for_replica(master.db, replica_ip)
			if len(indices_to_put) == 0:
				continue
			print replica_ip
			channel = grpc.insecure_channel(replica_ip)
			stub = search_pb2_grpc.ReplicaUpdateStub(channel)
			request = search_pb2.ReplicaRequest(data = data, master_ip = master.ip, create = 0)
			try:
				master.logger.info("Sending update message to replica " + replica_ip)
				response = stub.UpdateReplica(request)
				print(response)
				master.logger.info("Received " + str(response.status) + " from replica " + replica_ip)
				if response.status == 1:
					master.logger.info("Changing is_new in " + master.db + "db")
				else :
					master.logger.error("Replica db update failed")
			except Exception as e:
				print str(e)
				master.logger.error("Replica " + replica_ip + " not reachable due to " + str(e))

		# Backup
		if master.db == 'master':
			data, indices_to_put = get_data_for_backup(master.db)
			# print data, indices_to_put, len(data), len(indices_to_put)
			if not len(indices_to_put) == 0:
				channel = grpc.insecure_channel(master.master_backup_ip)
				stub = search_pb2_grpc.ReplicaUpdateStub(channel)
				request = search_pb2.ReplicaRequest(data = data, master_ip = master.ip, create = 0)
				try:
					master.logger.info("Sending update message to master backup " + master.master_backup_ip)
					response = stub.UpdateReplica(request)
					# print(response)
					master.logger.info("Received " + str(response.status) + " from master backup " + master.master_backup_ip)
					if response.status == 1:
						master.logger.info("Changing is_new in " + master.db + "db")
						updateMasterIndices(master.db, data)
					else :
						master.logger.error("Backup db update failed")
				except Exception as e:
					print str(e)
					print "Here!"
					master.logger.error("Master backup " + master.master_backup_ip + " not reachable due to " + str(e))


def heartbeatThread(db_name, master, replica_ip, location):
	channel = grpc.insecure_channel(replica_ip)
	stub = search_pb2_grpc.HealthCheckStub(channel)
	request = search_pb2.HealthCheckRequest(healthCheck = "is replica working?")
	try:
		master.logger.info("Sending heartbeat to replica")
		response = stub.Check(request, timeout = 5)
		print(response.status)
		print "REMOVING" + response.data
		words = query_metadatadb_indices(db_name, replica_ip)
		words_to_remove = response.data.split(' ')
		for word in words_to_remove:
			if word in words:
				words.remove(word)

			if location in master.loc_count and word in master.loc_count[location]:
				master.loc_count[location][word] = 0
				
			if location in master.cat_count and word in master.cat_count[location]:
				master.cat_count[location].remove(word)

		add_to_metadatadb(db_name, replica_ip, location, words)
		master.logger.info("Received " + str(response.status) + " from replica " + replica_ip)
	except Exception as e:
		print str(e)
		if str(e.code()) == "StatusCode.DEADLINE_EXCEEDED":
			print("DEADLINE_EXCEEDED!\n")
			master.logger.error("Deadline exceed - timeout before response received")
		if str(e.code()) == "StatusCode.UNAVAILABLE":
			print("UNAVAILABLE!\n")
			master.logger.error("Master server unavailable")


def sendHeartbeatsToReplicas(db_name, master):
	while True:
		for (replica_ip, location) in get_replica_ips_locs_from_metadatadb(db_name):
			thread.start_new_thread(heartbeatThread, (db_name, master, replica_ip, location))	

		time.sleep(5) # send heartbeat every 5 seconds


def serve(db_name, ip, backup, logging_level=logging.DEBUG, port='50051'):
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	master = Master(db_name, ip, backup, logging_level)
	search_pb2_grpc.add_SearchServicer_to_server(master, server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(master, server)
	write_service = WriteService(db_name, logger=master.logger)
	search_pb2_grpc.add_DatabaseWriteServicer_to_server(write_service, server)

	server.add_insecure_port('[::]:'+ port)
	server.start()
	master.logger.info("Starting server")
	print "Starting master"
	

	try:
		thread.start_new_thread(updateReplicaAndBackup, (master,))
	except Exception as e:
		print str(e)
		master.logger.error("Cannot start new thread due to " + str(e))

	try:
		thread.start_new_thread(sendHeartbeatsToReplicas, (db_name, master,))
	except Exception as e:
		print str(e)
		master.logger.error("Cannot start new thread due to " + str(e))
	
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
	backup = options.backup
	print ip, backup
	level = options.logging_level
	logging_level = parse_level(level)
	serve('master', ip, backup, logging_level)


if __name__ == '__main__':
	main()
