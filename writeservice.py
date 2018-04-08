'''Service to take care of writes'''
import json
from utils import addtodb, commitdb, rollbackdb
import search_pb2

class WriteService(object):
	def __init__(self, db_name, logger=None):
		self.db = db_name
		self.logger = logger

	def QueryToCommit(self, request, context):
		data = json.dumps(request.data)
		logger = self.logger
		try:
			if logger:
				logger.info("Adding to "+self.db+" database")
			addtodb(self.db, data)
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
				if logger:
					logger.info("Committing to "+self.db+" ...")
				commitdb(self.db)
				if logger:
					logger.info("Operation Success")
			elif request.code == search_pb2.ROLL_BACK:
				if logger:
					logger.info("Rolling back "+self.db+" ...")
				rollbackdb(self.db)
				if logger:
					logger.info("Operation Success")
		except Exception as e:
			print str(e)
			if logger:
				logger.info("Operation failed due to "+str(e))
				logger.info("Sending negative ACK")
			return search_pb2.Acknowledgement(status=0)
		if logger:
			logger.info("Sending positive ACK")
		return search_pb2.Acknowledgement(status=1)