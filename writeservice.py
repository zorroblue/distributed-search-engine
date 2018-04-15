'''Service to take care of writes'''
import json
from utils import *
import search_pb2

class WriteService(object):
	def __init__(self, db_name, logger=None):
		self.db = db_name
		self.logger = logger

	def WriteIndicesToTable(self, request, context):
		data = json.dumps(request.data)
		logger = self.logger
		try:
			if logger:
				logger.info("Adding to "+self.db+" database")
			addtodb(self.db, data)
			logger.info("Write operation success")
			return search_pb2.Acknowledgement(status=1)
		except Exception as e:
			print(str(e))
			logger.info("Write operation failed due to "+str(e))
			return search_pb2.Acknowledgement(status=0)

	# 2 phase commits
	def QueryToCommit(self, request, context):
		logger = self.logger
		try:
			if logger:
				logger.info("Adding to "+self.db+" database")
			print "indices: ", request.indices
			add_to_metadatadb(self.db, request.replica_ip, request.location, request.indices)
			if logger:
				logger.info("Operation success")
		except Exception as e:
			print(str(e))
			if logger:
				logger.info("Operation failed due to "+str(e))
				logger.info("Sending REJECT")
			return search_pb2.CommitVote(status=0)
		
		if logger:
			logger.info("Sending ACCEPT")
		return search_pb2.CommitVote(status=1)

	def CommitPhase(self, request, context):
		print request.code
		logger = self.logger
		try:
			if request.code == search_pb2.COMMIT:
				logger.info("Received COMMIT from master")
		except Exception as e:
			print str(e)
			if logger:
				logger.info("Operation failed due to "+str(e))
				logger.info("Sending negative ACK")
			return search_pb2.Acknowledgement(status=0)
		if logger:
			logger.info("Sending positive ACK")
		return search_pb2.Acknowledgement(status=1)