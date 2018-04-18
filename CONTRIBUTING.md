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

* Install [robomongo](https://askubuntu.com/questions/739297/how-to-install-robomongo-on-ubuntu/781793?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa) if you want to visualize the data changes on a GUI client(optional)

* Set up the database on the master and backup server
	
	`mongoimport --jsonArray -d masterdb -c indices data/indices.json` on master <br>

	`mongoimport --jsonArray -d backupdb -c indices data/indices.json` on backup of master`


* Set up the environment 

	`. environment.sh`


* Set up the required libraries

	`pip install -r requirements.txt`


* List the accessible replica servers in `replicas_list.txt`. The necessary setup as described above needs to be done. 
 
 ### Running the code

 #### To build the protobufs

 	python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. protos/search.proto

 ### Running the servers

Running `master.py`, `masterbackup.py` and `replica.py` with appropriate command line arguments should work. For running the crawler, use `crawler.py`. For demo purposes, we append the URLs in the URL list of 5 search terms with the input seed word during the writes. 
