from concurrent import futures
import time
import math

import grpc
import search_pb2
import search_pb2_grpc

from utils import querydb

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


class Master(search_pb2_grpc.SearchServicer):

	def __init__(self):
		# TODO : Add database
		self.db = None
		self._HEALTH_CHECK_TIME = 0

	def SearchForString(self, request, context):
		search_term = request.query
		urls = querydb('master', search_term)
		print "received query: ",search_term
		return search_pb2.SearchResponse(urls=urls)

	def Check(self, request, context):
		print request
		# if not self._HEALTH_CHECK_TIME%4:
		# 	time.sleep(2)
		self._HEALTH_CHECK_TIME += 1
		return search_pb2.HealthCheckResponse(status = "working_:)")

def serve():
	server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
	search_pb2_grpc.add_SearchServicer_to_server(Master(), server)
	search_pb2_grpc.add_HealthCheckServicer_to_server(Master(), server)
	server.add_insecure_port('[::]:50051')
	server.start()
	print "Starting master"
	try:
		while True:
			time.sleep(_ONE_DAY_IN_SECONDS)
	except KeyboardInterrupt:
		server.stop(0)


if __name__ == '__main__':
	serve()
