from motor import motor_asyncio as mongod

client = mongod.AsyncIOMotorClient('localhost', 27017)
db = client.maffin


async def findOne(collection, query):
	found = await db[collection].find_one(query)
	return found


def client():
	return db


# -----------------------Queues--------------------------------------------

async def get_queue(server_id, channel_id):
	doc = await get_setting(server_id, 'existing_queues')
	if doc is None:
		return None
	return doc[str(channel_id)]


async def update_queue(server_id, channel_id, new_queue):
	new_queue = {'$set': {str(channel_id): new_queue}}
	await update_setting(server_id, 'existing_queues', new_queue)


async def delete_queue(server_id, channel_id):
	await update_queue(server_id, channel_id, {'channel_id': channel_id})


# -----------------------------------------------------------------------------

# async def get_cog_settings(cogName):
# 	collection = 'settings'
# 	query = {"cog": cogName}
# 	cursor = db[collection].find(query)
# 	data = await cursor.to_list(length=999999999)
# 	res = {}
# 	for s in data:
# 		res[s['server_id']] = s
#
# 	return res

async def insert(server_id, collection, doc):
	collection = f'{collection}.s{server_id}'
	await db[collection].insert_one(doc)


async def get(server_id, collection, query, list=False):
	collection = f'{collection}.s{server_id}'
	res = db[collection].find(query)
	if list:
		res = await cursor.to_list(length=999999999)
	return res


async def update_setting(server_id, field_name, update):
	collection = f'settings.s{server_id}'
	query = {'field_name': field_name}
	await db[collection].update_one(query, update, upsert=True)


async def remove_setting(server_id, field_name, update):
	collection = f'settings.s{server_id}'
	query = {'field_name': field_name}
	await db[collection].remove(query, update, upsert=True)


async def get_setting(server_id, field_name):
	collection = f'settings.s{server_id}'
	query = {'field_name': field_name}
	res = await db[collection].find_one(query)
	if res is None:
		res = {}

	return res


async def get_all_settings(server_id):
	collection = f'settings.s{server_id}'
	query = {}
	cursor = db[collection].find(query)
	res = await cursor.to_list(length=999999999)
	return res
# -----------------------------------------------------------------------------

# async def get_permissions(server_id):
# 	collection = f'settings.{server_id}'
# 	query = {'channel_id': channel_id, 'field_name': "permissions"}
# 	document = await db[collection].find_one(query)
# 	return document

# async def get_settings(server_id):
# 	collection = 'settings'
# 	query = {'server_id': server_id}
# 	document = await db[collection].find_one(query)
# 	return document

# async def clear(collection):
# 	if collection != "heartbeat":
# 		raise ValueError  # No seas gil!
# 	await db.drop_collection(collection)
#
#
# async def find(collection, query):
# 	cursor = db[collection].find(query)
# 	data = await cursor.to_list(length=999999999)
# 	return data
#
#
# async def updateOne(collection, query, update):
# 	update = await db[collection].update_one(query, update, upsert=True)
# 	return update
#
#
# async def insertOne(collection, insert):
# 	await db[collection].insert_one(insert)
# 	return insert
#
#
# async def deleteOne(collection, query):
# 	found = await db[collection].delete_one(query)
# 	return found
