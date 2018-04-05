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
			default='localhost:50051',
			help='Replica IP address',
			required=False)
	return parser

def write_to_master_replica(master, replica, lower=51, higher=70):
	# generate data
	indices = generate_indices('pending', lower, higher)
	indices = json.dumps(indices)
	# initiate 2 phase commit protocol
	# Send CommitRequest
	channel = grpc.insecure_channel(master)
	stub = search_pb2_grpc.DatabaseWriteStub(channel)
	request = search_pb2.CommitRequest(data=indices)
	master_vote = stub.QueryToCommit(request)
	print "Status: ", master_vote.status
	

def main():
	parser = build_parser()
	options = parser.parse_args()
	master = options.master
	replica = options.replica
	# level = options.logging_level
	# logging_level = parse_level(level)
	write_to_master_replica(master=master, replica=replica)


if __name__ == '__main__':
	main()
