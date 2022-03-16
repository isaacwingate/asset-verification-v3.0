from pymongo import MongoClient

from server_variables import TXN_TIME_LIMIT

client = MongoClient(port=27017)

async def insertAwaitingTxn(username, user_id, addr, amount):
	db = client.AdaApocalypse.pendingTx

	pendingTx = {
	"user_id": user_id,
	"username": username,
	"addr": addr,
    "amount": amount,
	"status": "waiting",
	"attempts": 0
	}
	db.insert_one(pendingTx)

async def getAllPendingAddr():
	db = client.AdaApocalypse.pendingTx
	result = []
	result = db.find({"status": "waiting"},{"addr": 1, "username": 1, "user_id": 1, "amount": 1})
	return result

async def checkAttempts(addr, amount):
	db = client.AdaApocalypse.pendingTx
	result = db.find_one({"addr": addr, "status": "waiting", "amount": amount},{"attempts": 1, "user_id": 1})
	if int(result['attempts'] >= TXN_TIME_LIMIT):
		newValues = { "$set": {"status": "expired"} }
		db.update_one({"addr": str(addr),"status": "waiting", "amount": amount}, newValues)
		return result['user_id']
	else:
		newValues = { "$inc": {"attempts": 1} }
		db.update_one({"addr": str(addr),"status": "waiting", "amount": amount}, newValues)
		return None

async def searchCurrentMember(uID):
	db = client.AdaApocalypse.clubMembers
	result = db.find_one({"id": int(uID)},{})
	if result:
		return True
	return False

async def removeMember(mid):
	db = client.AdaApocalypse.clubMembers
	db.delete_many({"id": int(mid)})

async def removeTx(mid):
	db = client.AdaApocalypse.pendingTx
	db.delete_many({"user_id": int(mid)})

def findMember(user_id):
	db = client.CyberHorse.clubMembers
	return db.find_one({"id": user_id},{"addr": 1})

# insert member to db
async def insertMember(mid,name,addr,txn, asset_cnt, userWallet):
	db = client.AdaApocalypse.clubMembers
	member = {
	"id": mid,
	"name": name,
	"addr": addr,
	"txn": txn,
	"ass_cnt": asset_cnt,
	"og_holder": userWallet['OG_HOLDER'],
	"horder_holder": userWallet['HORDER_HOLDER'],
	"large_whale": userWallet['LARGE_WHALE'],
	"small_whale": userWallet['SMALL_WHALE'],
	"no_eyes": userWallet['NO_EYES'],
	"trippy_eyes": userWallet['TRIPPY_EYES'],
	"gold_skin": userWallet['GOLD_SKIN'],
	"laser_eyes": userWallet['LASER_EYES']

	}
	db.insert_one(member)


async def updatePendingTxn(addr, amount):
    db = client.AdaApocalypse.pendingTx
    newValues = { "$set": {"status": "payment_received"} }
    db.update_one({"addr": str(addr), "amount": amount, "status": "waiting"}, newValues)

# update member
async def updateRoleResweep(id, cnt, userWallet):
	db = client.AdaApocalypse.clubMembers

	newValues = { "$set": {
	"ass_cnt": cnt, 
	"og_holder": userWallet['OG_HOLDER'],
	"horder_holder": userWallet['HORDER_HOLDER'],
	"large_whale": userWallet['LARGE_WHALE'],
	"small_whale": userWallet['SMALL_WHALE'],
	"no_eyes": userWallet['NO_EYES'],
	"trippy_eyes": userWallet['TRIPPY_EYES'],
	"gold_skin": userWallet['GOLD_SKIN'],
	"laser_eyes": userWallet['LASER_EYES']} }
	
	db.update_one({"id": int(id)}, newValues)


async def get_all_addr():
	db = client.AdaApocalypse.clubMembers
	addresses = []
	result = db.find({},{"addr":1,"id":1,"name":1, "ass_cnt":1})
	for x in result:
		addresses.append({"id": str(x['id']),"addr": str(x['addr']),"name": str(x['name']), "asset_count": x['ass_cnt']})
	return addresses

async def removeAddr(addr):
	db = client.AdaApocalypse.clubMembers
	db.delete_one({"addr": str(addr)})

async def checkAddrExists(addr):
	db = client.AdaApocalypse.clubMembers
	result = db.find_one({"addr":str(addr)})
	if result:
		return True
	return False