import requests
from bot import print_log
from server_variables import *
import pprint
pp = pprint.PrettyPrinter(indent=4).pprint

def checkTxn(addr, amount):
	amount *= 1000000
	amount = int(amount)
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(addr)+"/utxos"
	auth = {'project_id' : BLOCKFROST_KEY}

	response = requests.get(api_url,headers=auth)
	#pp(response.json())
	if response.json():
		try:
			for x in response.json():
				if int(x['amount'][0]['quantity']) == int(amount):
					txn = x['tx_hash']
					txn_url = "https://cardano-mainnet.blockfrost.io/api/v0/txs/"+str(txn)+"/utxos"
					txn_response = requests.get(txn_url,headers=auth)
					for y in txn_response.json()['outputs']:
						if y['address'] == addr and y['amount'][0]['quantity'] == str(amount):
							return txn
		except:
			pass
	return False

#print(checkTxn('addr1q8j40z44jt7et7655mh0z8gtvhsyvku8g33j0yuezcz30xe60533pwn4daffgxvws0uexw39gxmnug9g77fnmx96z9eqeukp8m',6))

def binSearch(num, arr):
	low = 0
	high = len(arr) - 1

	while low <= high:
		middle = low + (high - low) // 2
		if arr[middle] == num:
			return True
		elif arr[middle] < num:
			low = middle + 1
		else:
			high = middle - 1
	return False

# search wallet for assets
def searchAddr(addr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/accounts/"+str(addr)+"/addresses/assets"
	auth = {'project_id' : BLOCKFROST_KEY}
	cnt = 0

	hasOG, hasHorder = False, False
	hasNoEyes, hasTrippyEyes, hasGoldSkin, hasLaserEyes = False, False, False, False
	checkNoEyes, checkTrippyEyes, checkGoldSkin, checkLaserEyes = True, True, True, True

	smallWhale, largeWhale = False, False

	page = 1
	while(True):
		param = {'page' : page}
		response = requests.get(api_url,headers=auth, params=param)
		if response.json():
			for x in response.json():
				asset_id = str(x['unit'])

				# if OG Policy
				if asset_id.startswith(OG_POLICY):
					hasOG = True
					cnt += 1
					
					# check if asset is top 1000
					if checkNoEyes or checkTrippyEyes or checkGoldSkin:
						asset_url = "https://cardano-mainnet.blockfrost.io/api/v0/assets/" + str(asset_id)
						asset_response = requests.get(asset_url,headers=auth, params=param)
						asset_name = asset_response.json()['onchain_metadata']['name']
						try:
							asset_num = int(asset_name.split("#")[1])

							if checkNoEyes and binSearch(asset_num, NO_EYES):
								hasNoEyes, checkNoEyes = True, False

							if checkTrippyEyes and binSearch(asset_num, TRIPPY_EYES):
								hasTrippyEyes, checkTrippyEyes = True, False

							if checkGoldSkin and binSearch(asset_num, GOLD_SKIN):
								hasGoldSkin, checkGoldSkin = True, False
						except Exception as e:
							print_log(str(e))


					# check for traits here
				elif asset_id.startswith(HORDER_POLICY):
					hasHorder = True
					cnt += 1

					if checkLaserEyes:
						asset_url = "https://cardano-mainnet.blockfrost.io/api/v0/assets/" + str(asset_id)
						asset_response = requests.get(asset_url,headers=auth, params=param)
						asset_name = asset_response.json()['onchain_metadata']['name']
						asset_num = int(asset_name.split("#")[1])

						if binSearch(asset_num, LASER_EYES):
							hasLaserEyes, checkLaserEyes = True, False

						
			page +=1
		else:
			if cnt >= 30:
				largeWhale = True
			elif cnt >= 15:
				smallWhale = True

			return cnt, {"OG_HOLDER": hasOG, "HORDER_HOLDER": hasHorder, "SMALL_WHALE": smallWhale, "LARGE_WHALE": largeWhale,
						"NO_EYES": hasNoEyes, "TRIPPY_EYES": hasTrippyEyes, "GOLD_SKIN": hasGoldSkin, "LASER_EYES": hasLaserEyes}

async def getStakeAddr(userAddr):
	api_url = "https://cardano-mainnet.blockfrost.io/api/v0/addresses/"+str(userAddr)
	auth = {'project_id' : BLOCKFROST_KEY}
	response = requests.get(api_url,headers=auth)
	if response.json():
		stakeAddr = response.json()['stake_address']
		return str(stakeAddr)
	return ""