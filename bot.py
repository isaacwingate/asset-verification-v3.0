import discord
from discord import user
from discord_components import ComponentsBot
from discord.ext import commands
import random
import asyncio
import warnings
from threading import Thread
from time import sleep
from threading import Lock
from datetime import datetime
w_mutex = Lock()

from server_variables import *
from wallet_interaction import *
from handle_db import *



warnings.filterwarnings("ignore")
intents = discord.Intents(members = True, messages=True, guilds=True, presences=True)

user_ids = []
active = False
discord_client = ComponentsBot("/",intents = intents)

################################################################
async def check_owner(ctx):
	is_owner = await ctx.bot.is_owner(ctx.author)
	if is_owner:
		return True
	else:
		return False

def is_owner():
	async def pred(ctx):
		return await check_owner(ctx)
	return commands.check(pred)

def is_dm():
    async def pred(ctx):
        return isinstance(ctx.channel, discord.channel.DMChannel)
    return commands.check(pred)

async def dm_user(uid, msg):
	user = discord_client.get_user(int(uid))
	await user.send(str(msg))
################################################################
@discord_client.command()
@is_owner()
async def start(ctx):
	global active
	active = True
	print_log("VERIFICATION GOING ACTIVE")
	await ctx.send("OK")
	return

@discord_client.command()
@is_owner()
async def stop(ctx):
	global active
	active = False
	print_log("STOPPING VERIFICATION ACTIVITIES")
	await ctx.send("OK")

@discord_client.command()
@is_owner()
async def give_whale(ctx):
    guild = discord_client.get_guild(SERVER_ID)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)

    member = guild.get_member(339011064660492288)
    await member.add_roles(whale_role)

    await ctx.send("Whale role given")

@discord_client.command()
@is_owner()
async def remove_whale(ctx):
    guild = discord_client.get_guild(SERVER_ID)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)

    member = guild.get_member(339011064660492288)
    await member.remove_roles(whale_role)

    await ctx.send("Whale role removed")

def print_log(log):
	now = datetime.now()
	current_time = now.strftime("%d/%m/%y %H:%M:%S")
	print(current_time + " - " + log)
	return

###################		INIT BOT 		############################

def init_discord_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(discord_client.start(DISCORD_TOKEN))
    t = Thread(target=loop.run_forever)
    t.daemon = True #terminates when main thread terminates. this is important
    t.start()

async def client_start():
    await discord_client.start(DISCORD_TOKEN)  

@discord_client.event
async def on_ready():
	print("Discord bot logged in as: %s, %s" % (discord_client.user.name, discord_client.user.id))

###################		 		############################
def check(author):
    def inner_check(message):
        return message.author == author and message.content != ""
    return inner_check

async def checkAddrFormat(addr, ctx, firstMsg=False):
    if addr.startswith('addr1'):
        return True
    if not firstMsg:
        await ctx.send('Incorrect msg, check formatting')
    return False

async def checkTxnFormat(txn, ctx, firstTxn):
    if len(txn) == 64:
        return True
    if not firstTxn:
        await ctx.send('Incorrect msg, check formatting')
    return False
###################		Check Pending Transactions 		############################

@discord_client.event
async def on_check_pending_tx():
    guild = discord_client.get_guild(SERVER_ID)
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)

    print_log("Checking pending tx's.")

    pendingAddr = []
    pendingAddr = await getAllPendingAddr()

    for a in pendingAddr:
        username = str(a['username'])
        user_id = a['user_id']
        txn = a['txn']
        addr = a['addr']
        amount = a['amount']

        if await checkTxn(txn, addr, amount):
            await updatePendingTxn(addr, txn)
            
            stakeAddr = await getStakeAddr(addr)

            if stakeAddr == "":
                print_log("ERROR: unable to find " + str(a['username']) + " stake addr.")
                dm_user(user_id, "Unable to find stake addr, please try again.")
                return

            if await checkAddrExists(stakeAddr):
                await dm_user(user_id, "ERROR: Address has already been registered")
                print_log("Error: " + str(username) + " stake addr already registered")
                return

            asset_count = await searchAddr(stakeAddr)

            if asset_count >= 1:
                member = guild.get_member(user_id)
                if member:
                    await member.add_roles(role)
                    if asset_count >= 25:
                        await member.add_roles(whale_role)
                    await insertMember(user_id, str(username), str(stakeAddr), str(txn), asset_count)

                    print_log(str(member.name) + " has been verified")
                    await dm_user(user_id, "You have been verified!")
                else:
                    print_log("Couldn't find member obj in db for " + str(username))
            else:
                print_log(str(username) + " Does not have the required NFT")
                await dm_user(user_id, "Could not find the required NFT in your wallet, try again later.")

        else:
            #increment attemtps
            expired_user_id = await checkAttempts(str(a['addr']))
            if expired_user_id:
                await dm_user(expired_user_id, "Error: Please use /join to try again!")

###################		Resweep Registered Members 		############################

@discord_client.event
async def on_resweep():
    guild = discord_client.get_guild(SERVER_ID)
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)
    print_log("Initiating resweep.")

    addresses = await get_all_addr()

    for addr in addresses:
        asset_count = await searchAddr(addr['addr'])
        if asset_count == 0:
            member = guild.get_member(int(addr['id']))
            if member:
                print_log(str(addr['addr']) + " no longer has the required NFT")
                await member.remove_roles(role)
                
                # remove record from DB
                await removeAddr(addr['addr'])
                print_log(str(addr['name']) + " has been removed, address: " + str(addr['addr']))
        elif asset_count >= 25:
            await updateAssetCount(addr['addr'], asset_count)
            try:
                await member.add_roles(whale_role)
            except Exception as e:
                print_log(str(e))
        else:
            await updateAssetCount(addr['addr'], asset_count)
            try:
                await member.remove_roles(whale_role)
            except Exception as e:
                print_log(str(e))


                

###################		DM BOT 		############################
@discord_client.command()
@is_dm()
async def join(ctx):
    if active and ctx.author.id not in user_ids:
        await ctx.send("starting verification process")
        user_id = ctx.author.id
        username = str(ctx.author.name)

        user_ids.append(user_id)

        print_log(username + " has started verification process")
        
        firstMsg = True
        addr = ""

        while not await checkAddrFormat(addr, ctx, firstMsg):
            try:
                firstMsg = False
                # request user addr
                await ctx.send("Please enter your wallet address: ")
                addr = await discord_client.wait_for('message', check=check(ctx.author), timeout=120)
                addr = addr.content
                
            except:
                await ctx.send('You took too long! Type /join to try again.')
                user_ids.remove(user_id)
                return
        
        await ctx.send('Addr succsfully captured')

        amount = round(random.uniform(2.000, 3.000),3)

        await ctx.send('Please send ' + str(amount) + " ADA to your address")

        

        firstTxn = True
        txn = ""

        while not await checkTxnFormat(txn, ctx, firstTxn):
            try:
                firstTxn = False
                # request user addr
                await ctx.send("Please enter the txn ID: ")
                txn = await discord_client.wait_for('message', check=check(ctx.author), timeout=300)
                txn = txn.content            
            except:
                await ctx.send('You took too long! Type /join to try again.')
                user_ids.remove(user_id)
                return

        #insert awaiting txn to db
        await insertAwaitingTxn(username, user_id, txn, addr, amount)

        await ctx.send('Thanks! Please wait while the txn confirms')
        

###################		Main 		############################

if __name__ == "__main__":
	mins = 0
	init_discord_bot()
	while True:
		sleep(60) #half a day
		if active:
			mins += 1
			if mins == 720:
				mins = 0
				discord_client.dispatch("resweep") #send this event to bot every half a day
			else:
				discord_client.dispatch("check_pending_tx") #send this event to bot every half a day5