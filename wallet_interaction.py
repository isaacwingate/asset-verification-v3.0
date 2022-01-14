import requests

from server_variables import *
import pprint
pp = pprint.PrettyPrinter(indent=4).pprint

async def checkTxn(txn, addr, amount):
    amount *= 1000000
    api_url = "https://cardano-mainnet.blockfrost.io/api/v0/txs/"+str(txn)+"/utxos"
    auth = {'project_id' : BLOCKFROST_KEY}

    response = requests.get(api_url,headers=auth)

    if response.json():
        for x in response.json()['inputs']:
            if int(x['amount'][0]['quantity']) == int(amount):
                return True
        for x in response.json()['outputs']:
            if int(x['amount'][0]['quantity']) == int(amount):
                return True
    else:
        return False

async def searchAddr(addr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/accounts/"+addr+"/addresses/assets"
	auth = {'project_id' : BLOCKFROST_KEY}

	count = 0
	page = 1
	while(True):
		param = {'page' : page}
		response = requests.get(api_url,headers=auth, params=param)
		if response.json():
			for x in response.json():
				for p in POLICY:
					if str(x['unit']).startswith(p):
						count += 1
			page +=1
		else:
			return count

async def getStakeAddr(userAddr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(userAddr)
	auth = {'project_id' : BLOCKFROST_KEY}
	response = requests.get(api_url,headers=auth)
	if response.json():
		stakeAddr = response.json()['stake_address']
		return str(stakeAddr)
	return ""