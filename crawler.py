from concurrent import futures
import time
import math

from argparse import ArgumentParser
import argparse

import grpc
import search_pb2
import search_pb2_grpc

import json
import logging

from utils import querydb, init_logger, parse_level
from data.generatedata import generate_indices

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def build_parser():
	parser = ArgumentParser()
	parser.add_argument('--master',
			dest='master', help='Master IP address',
			default='localhost:50051',
			required=False)
	parser.add_argument('--replica',
			dest='replica',
			default='localhost:50052',
			help='Replica IP address',
			required=False)
	choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
	parser.add_argument('--logging',
			dest='logging_level', help='Logging level',
			choices=choices,
			default='DEBUG',
			required=False)
	return parser


def write_to_master_replica(master, replica, logging_level, lower=51, higher=70):
	# initialize logger
	logger = init_logger('crawler', logging_level)
	# generate data
	indices = generate_indices('pending', lower, higher)
	indices = json.dumps(indices)
	# initiate 2 phase commit protocol
	
	# PHASE 1
	logger.debug("Initiate 2 phase commit protocol")
	print "Phase 1: Prepare"
	logger.debug("Starting Phase 1: Prepare")

	master_vote = None
	replica_vote = None
	
	master_channel = grpc.insecure_channel(master)
	master_stub = search_pb2_grpc.DatabaseWriteStub(master_channel)
	
	request = search_pb2.CommitRequest(data=indices)

	replica_channel = grpc.insecure_channel(replica)
	replica_stub = search_pb2_grpc.DatabaseWriteStub(replica_channel)

	try:
		logger.info("Send COMMIT_REQUEST to master")
		master_vote = master_stub.QueryToCommit(request)
		print "Master Status: ", master_vote.status
		if master_vote.status == 1:
			logger.info("Received AGREED from master")
		else:
			logger.info("Received ABORT from master")
	except Exception as e:
		print e.code()
		logger.error("Master not reachable due to "+ str(e.code()))

	try:
		logger.info("Send COMMIT_REQUEST to backup")
		replica_vote = replica_stub.QueryToCommit(request)
		print "Backup Status: ", replica_vote.status
		if replica_vote.status == 1:
			logger.info("Received AGREED from backup")
		else:
			logger.info("Received ABORT from backup")
	except Exception as e:
		print e.code()
		logger.error("Backup not reachable due to "+ str(e.code()))
	
	# PHASE 2
	print "Phase 2: Prepare"
	logger.debug("Starting Phase 2: Commit")

	if master_vote == None or replica_vote == None or replica_vote.status == 0 or master_vote.status == 0:
		try:
			request = search_pb2.CommitStatusUpdate(code=search_pb2.ROLL_BACK)
			try:
				logger.info("Sending ROLL_BACK to master")
				master_ack = master_stub.CommitPhase(request)
			except Exception as e:
				print str(e)
				logger.info("Master not able to receive ROLL_BACK due to "+ str(e.code()))
			
			try:
				logger.info("Sending ROLL_BACK to replica")
				replica_ack = replica_stub.CommitPhase(request)
			except Exception as e:
				print str(e)
				logger.info("Replica not able to receive ROLL_BACK due to "+ str(e.code()))

		except Exception as e:
			print e.code()
		logger.info("Rolled back transaction")
		return False

	# Commit Phase
	request = search_pb2.CommitStatusUpdate(code=search_pb2.COMMIT)
	master_ack_received = False
	replica_ack_received = False
	retries = 0
	
	while (not master_ack_received or not replica_ack_received) and retries < 3: 
		if retries > 0:
			logger.info("Retrying")
		if not master_ack_received:
			try:
				logger.info("Sending COMMIT to master")
				master_ack = master_stub.CommitPhase(request)
				master_ack_received = True
			except Exception as e:
				logger.info("Master failed to receive due to "+ str(e.code()))
		if not replica_ack_received:
			try:
				logger.info("Sending COMMIT to backup")
				replica_ack = replica_stub.CommitPhase(request)
				replica_ack_received = True
			except Exception as e:
				logger.info("Backup failed to receive due to "+ str(e.code()))
		retries+=1
		print master_ack_received, replica_ack_received
		

	if retries < 3:
		logger.info("COMMIT")
		# TODO rollback 
		# not doing it now to progress further in the work
		# PS if one of them fails, they will resync with the crawler. The crawler is aware of this as COMMIT isn't written till then.

	print "Phase 2:"
	print "Master status", master_ack.status
	print "Replica status", replica_ack.status
	return master_ack.status == 1 and replica_ack.status == 1


def main():
	parser = build_parser()
	options = parser.parse_args()
	master = options.master
	replica = options.replica
	logging_level = parse_level(options.logging_level)
	status = write_to_master_replica(master=master, replica=replica, logging_level=logging_level)
	if status:
		print "Write successful"

if __name__ == '__main__':
	main()
