from motor import motor_asyncio as mongod
client = mongod.AsyncIOMotorClient('localhost', 27017)
db = client.oompaLoompa

async def findOne(collection,query):
	found = await db[collection].find_one(query)
	return found

def client():
	return db

async def find(collection,query):
	cursor =  db[collection].find(query)
	data = await cursor.to_list(length=999999999)
	return data

async def updateOne(collection, query, update):
	update = await db[collection].update_one(query, update,upsert=True)
	return update

async def insertOne(collection, insert):
	await db[collection].insert_one(insert)
	return insert

async def deleteOne(collection,query):
	found = await db[collection].delete_one(query)
	return found


# async def getIndex(collection,key,query):
# 	cursor = db[collection].find({key:query})
# 	index = await cursor.to_list(length=None)
# 	index = len(index)
# 	return index + 1

# async def getLeaderboard(collection,key):
# 	cursor = db[collection].find({}).sort(key,-1)
# 	data = []
# 	for document in await cursor.to_list(length=20):
# 		data.append(document)
# 	return data


