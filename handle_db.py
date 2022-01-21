from pymongo import MongoClient


client = MongoClient(port=27017)

async def insertAwaitingTxn(username, user_id, txn, addr, amount):
	db = client.Benjamin.pendingTx

	pendingTx = {
	"user_id": user_id,
	"username": username,
	"addr": addr,
    "txn": txn,
    "amount": amount,
	"status": "waiting",
	"attempts": 0
	}
	try:
		db.insert_one(pendingTx)
	except Exception as e:
		print("Error occured adding to pendingTx DB - " + str(username) + " (" +str(e)+")")

async def getAllPendingAddr():
	db = client.Benjamin.pendingTx
	result = []
	result = db.find({"status": "waiting"},{"addr": 1, "username": 1, "user_id": 1, "txn": 1, "amount": 1})
	return result

async def checkAttempts(addr):
	db = client.Benjamin.pendingTx
	result = db.find_one({"addr": addr, "status": "waiting"},{"attempts": 1, "user_id": 1})
	if int(result['attempts'] >= 15):
		newValues = { "$set": {"status": "expired"} }
		db.update_one({"addr": str(addr)}, newValues)
		return result['user_id']
	else:
		newValues = { "$inc": {"attempts": 1} }
		db.update_one({"addr": str(addr)}, newValues)
		return None

async def searchCurrentMember(uID):
	db = client.Benjamin.clubMembers
	result = db.find_one({"id": int(uID)},{})
	if result:
		return True
	return False

async def removeMember(mid):
	db = client.Benjamin.clubMembers
	db.delete_many({"id": int(mid)})

async def removeTx(mid):
	db = client.Benjamin.pendingTx
	db.delete_many({"id": int(mid)})

async def insertMember(mid,name,addr,txn,asset_count):
    db = client.Benjamin.clubMembers

    member = {
    "id": mid,
    "name": name,
    "addr": addr,
    "txn": txn,
	"asset_count": asset_count
    }
    if searchCurrentMember(mid):
        await removeMember(mid)
    try:
        db.insert_one(member)
    except Exception as e:
        print("Error occured adding to DB - " + str(name) + " (" +str(e)+")")

async def updatePendingTxn(addr, txn):
    db = client.Benjamin.pendingTx
    newValues = { "$set": {"status": "payment_received"} }
    db.update_one({"addr": str(addr), "txn": str(txn)}, newValues)

async def updateAssetCount(addr, asset_count):
	db = client.Benjamin.clubMembers
	newValues = { "$set": {"asset_count": int(asset_count)} }
	db.update_one({"addr": str(addr)}, newValues)


async def get_all_addr():
	db = client.Benjamin.clubMembers
	addresses = []
	result = db.find({},{"addr":1,"id":1,"name":1, "asset_count":1})
	for x in result:
		addresses.append({"id": str(x['id']),"addr": str(x['addr']),"name": str(x['name']), "asset_count": x['asset_count']})
	return addresses

async def removeAddr(addr):
	db = client.Benjamin.clubMembers
	db.delete_one({"addr": str(addr)})

async def checkAddrExists(addr):
	db = client.Benjamin.clubMembers
	result = db.find_one({"addr":str(addr)})
	if result:
		return True
	return False