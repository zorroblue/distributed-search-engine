# Contribution guidelines:

## General guidelines:

* Abstract stuff as much as you can, design code in such a way that minimum hardcoding is done inside the code.

* IPs and any device specific parameters should be passed as sysargs while running the code.

* Write all communication requests/responses in terms of RPC calls. We use gRPC for the same.


## To run the code

### Basic setup:

* Clone the repository

	`git clone https://github.com/zorroblue/distributed-search-engine`

* Create a virtual environment venv if not done already

	`cd distributed-search-engine` <br>
	`virtualenv venv` <br>

* Install mongodb 3.2.12

* Set up the database on the master and backup server
	
	`mongoimport --jsonArray -d masterdb -c indices data/indices.json` on master <br>

	`mongoimport --jsonArray -d backupdb -c indices data/indices.json` on backup of master`


* Set up the environment 

	`. environment.sh`


* Set up the required libraries

	`pip install -r requirements.txt`

 
 ### Running the code

 #### To build the protobufs

 	python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/search.proto

 #### Defaults:

 	The master server runs in port 50051 while replica runs in port 50052. The database name of master is 'masterdb' while replica's is 'replicadb'