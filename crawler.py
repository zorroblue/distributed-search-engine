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
	return parser


def write_to_master_replica(master, replica, lower=51, higher=70):
	# generate data
	indices = generate_indices('pending', lower, higher)
	indices = json.dumps(indices)
	# initiate 2 phase commit protocol
	
	# Send CommitRequest
	master_channel = grpc.insecure_channel(master)
	master_stub = search_pb2_grpc.DatabaseWriteStub(master_channel)
	request = search_pb2.CommitRequest(data=indices)
	master_vote = master_stub.QueryToCommit(request)
	print "Phase 1:"
	print "Master Status: ", master_vote.status
	replica_channel = grpc.insecure_channel(replica)
	replica_stub = search_pb2_grpc.DatabaseWriteStub(replica_channel)
	replica_vote = replica_stub.QueryToCommit(request)
	print "Replica Status: ", replica_vote.status
	
	# Commit Phase
	if replica_vote.status == 1 and replica_vote.status == 1:
		request = search_pb2.CommitStatusUpdate(code=search_pb2.COMMIT)
	else:
		request = search_pb2.CommitStatusUpdate(code=search_pb2.ROLL_BACK)
	master_ack = master_stub.CommitPhase(request)
	replica_ack = replica_stub.CommitPhase(request)
	print "Phase 2:"
	print "Master status", master_ack.status
	print "Replica status", replica_ack.status


def main():
	parser = build_parser()
	options = parser.parse_args()
	master = options.master
	replica = options.replica
	# level = options.logging_level
	# logging_level = parse_level(level)
	status = write_to_master_replica(master=master, replica=replica)
	print "Write successful"

if __name__ == '__main__':
	main()
