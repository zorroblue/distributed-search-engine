from concurrent import futures
import time
import math

import grpc
import search_pb2
import search_pb2_grpc

from utils import querydb

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Master(search_pb2_grpc.SearchServicer):

	def __init__(self, db_name):
		
		self.db = db_name
		self._HEALTH_CHECK_TIME = 0

	def SearchForString(self, request, context):
		search_term = request.query
		urls = querydb(self.db, search_term)
		print("Received query: " + search_term+"\n")
		return search_pb2.SearchResponse(urls=urls)

	def Check(self, request, context):
		print request
		self._HEALTH_CHECK_TIME += 1
		return search_pb2.HealthCheckResponse(status = "STATUS: Master server up!")


def serve(db_name):
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	# TODO: Check if the first param for both the below should be the same object
	search_pb2_grpc.add_SearchServicer_to_server(Master(db_name), server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(Master(db_name), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	print "Starting master"
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__ == '__main__':
	serve('master')
