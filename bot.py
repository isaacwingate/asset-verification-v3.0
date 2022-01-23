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

async def dm_user(uid, msg, colour):
    user = discord_client.get_user(int(uid))

    emb=discord.Embed(description=msg, colour = colour)
    emb.set_author(name="Asset Verification Bot", icon_url=PFP)

    await user.send(embed=emb)

def print_log(log):
    now = datetime.now()
    current_time = now.strftime("%d/%m/%y %H:%M:%S")
    print(current_time + " - " + log)
    return
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


###################		INIT BOT 		############################

def init_discord_bot():
    loop = asyncio.get_event_loop()
    loop.create_task(client_start())
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

async def checkAddrFormat(addr, user_id, firstMsg=False):
    if addr.startswith('addr1'):
        return True
    if not firstMsg:
        #await ctx.send('Incorrect msg, check formatting')
        await dm_user(user_id, "Incorrect address, check formatting", discord.Colour.red())
    return False

async def checkTxnFormat(txn, user_id, firstTxn):
    if len(txn) == 64:
        return True
    if not firstTxn:
        #await ctx.send('Incorrect msg, check formatting')
        await dm_user(user_id, "Incorrect txn ID, check formatting", discord.Colour.red())
    return False
###################		Check Pending Transactions 		############################

@discord_client.event
async def on_check_pending_tx():
    guild = discord_client.get_guild(SERVER_ID)
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)
    dozen_role = discord.utils.get(guild.roles, name=ROLE_NAME_DOZEN)

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
                dm_user(user_id, "Unable to find stake addr, please try again.", discord.Colour.red())
                return

            if await checkAddrExists(stakeAddr):
                await dm_user(user_id, "ERROR: Address has already been registered", discord.Colour.red())
                print_log("Error: " + str(username) + " stake addr already registered")
                return

            asset_count = await searchAddr(stakeAddr)

            if asset_count >= 1:
                member = guild.get_member(user_id)
                if member:
                    await member.add_roles(role)
                    if asset_count >= 25:
                        await member.add_roles(whale_role)
                    elif asset_count >= 12:
                        await member.add_roles(dozen_role)
                    await insertMember(user_id, str(username), str(stakeAddr), str(txn), asset_count)

                    print_log(str(member.name) + " has been verified")
                    await dm_user(user_id, "You have been verified!", discord.Colour.green())
                    if user_id in user_ids:
                        user_ids.remove(user_id)
                else:
                    print_log("Couldn't find member obj in db for " + str(username))
            else:
                print_log(str(username) + " Does not have the required NFT")
                await dm_user(user_id, "Could not find the required NFT in your wallet, try again later.", discord.Colour.red())
                if user_id in user_ids:
                    user_ids.remove(user_id)

        else:
            #increment attemtps
            expired_user_id = await checkAttempts(str(a['addr']))
            if expired_user_id:
                await dm_user(expired_user_id, "Error: Please use /join to try again!", discord.Colour.red())
                user_ids.remove(user_id)

###################		Resweep Registered Members 		############################

@discord_client.event
async def on_resweep():
    guild = discord_client.get_guild(SERVER_ID)
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)
    dozen_role = discord.utils.get(guild.roles, name=ROLE_NAME_DOZEN)
    print_log("Initiating resweep.")

    addresses = await get_all_addr()

    for addr in addresses:
        asset_count = await searchAddr(addr['addr'])
        old_asset_count = int(addr['asset_count'])

        
        member = guild.get_member(int(addr['id']))
        if member:
            if asset_count == 0:
                print_log(str(addr['addr']) + " no longer has the required NFT")

                if ROLE_NAME_WHALE in [x.name for x in member.roles]:   # remove whale role
                    await member.remove_roles(whale_role)
                if ROLE_NAME_DOZEN in [x.name for x in member.roles]:   # remove dozen role
                    await member.remove_roles(dozen_role)
                if ROLE_NAME in [x.name for x in member.roles]:         # remove Con role
                    await member.remove_roles(role)
                
                # remove record from DB
                await removeAddr(addr['addr'])
                print_log(str(addr['name']) + " has been removed, address: " + str(addr['addr']))

            elif asset_count != old_asset_count:
                await updateAssetCount(addr['addr'], asset_count)
                if asset_count >= 25:
                    if ROLE_NAME_WHALE not in [x.name for x in member.roles]:
                        await member.add_roles(whale_role)
                    if ROLE_NAME_DOZEN in [x.name for x in member.roles]:
                        await member.remove_roles(dozen_role)
                elif asset_count >= 12:
                    if ROLE_NAME_WHALE in [x.name for x in member.roles]:
                        await member.remove_roles(whale_role)
                    if ROLE_NAME_DOZEN not in [x.name for x in member.roles]:
                        await member.add_roles(dozen_role)

                #Norm role
                if ROLE_NAME not in [x.name for x in member.roles]:
                    await member.add_roles(role)

                print_log(str(addr['name'] + " count has changed from " + str(old_asset_count) + " to " + str(asset_count)))

                

###################		DM BOT 		############################
@discord_client.command()
@is_dm()
async def reset(ctx):
    guild = discord_client.get_guild(SERVER_ID)
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    whale_role = discord.utils.get(guild.roles, name=ROLE_NAME_WHALE)
    dozen_role = discord.utils.get(guild.roles, name=ROLE_NAME_DOZEN)

    user_id = ctx.author.id
    member = guild.get_member(int(user_id))
    username = str(ctx.author.name)
    if user_id in user_ids:
        user_ids.remove(user_id)
    await removeMember(user_id)
    await removeTx(user_id)

    if ROLE_NAME_WHALE in [x.name for x in member.roles]:   # remove whale role
        await member.remove_roles(whale_role)
    if ROLE_NAME_DOZEN in [x.name for x in member.roles]:   # remove dozen role
        await member.remove_roles(dozen_role)
    if ROLE_NAME in [x.name for x in member.roles]:         # remove Con role
        await member.remove_roles(role)

    #await ctx.send('Reset succesfully! Type /join to try again.')
    await dm_user(user_id, "Reset succesful! Type /join to try again.", discord.Colour.green())
    print_log(username + " has used /reset")
    return

@discord_client.command()
@is_dm()
async def join(ctx):
    if active and ctx.author.id not in user_ids:
        guild = discord_client.get_guild(SERVER_ID)
        user_id = ctx.author.id
        member = guild.get_member(int(user_id))
        username = str(ctx.author.name)

        user_ids.append(user_id)

        if ROLE_NAME in [x.name for x in member.roles]:
            await dm_user(user_id, "You have already been verified! Type /reset to link a new wallet", discord.Colour.orange())
            print_log(str(username) + " is already verified.")
            return

        print_log(username + " has started verification process")
        
        firstMsg = True
        addr = ""

        while not await checkAddrFormat(addr, user_id, firstMsg):
            try:
                firstMsg = False
                # request user addr
                await dm_user(user_id, "Please enter your wallet address: ", discord.Colour.blue())
                #await ctx.send()
                addr = await discord_client.wait_for('message', check=check(ctx.author), timeout=120)
                addr = addr.content
                
            except:
                #await ctx.send('You took too long! Type /join to try again.')
                await dm_user(user_id, "You took too long! Type /join to try again.", discord.Colour.red())
                if user_id in user_ids:
                    user_ids.remove(user_id)
                return
        
        #await ctx.send('Addr succesfully captured')

        amount = round(random.uniform(2.000, 3.000),3)

        #await ctx.send('Please send ' + str(amount) + " ADA to your address")
        await dm_user(user_id,'Please send ' + str(amount) + " ADA to your address" , discord.Colour.blue())

        

        firstTxn = True
        txn = ""

        while not await checkTxnFormat(txn, user_id, firstTxn):
            try:
                firstTxn = False
                # request user addr
                await dm_user(user_id, "Please enter the txn ID: ", discord.Colour.blue())
                txn = await discord_client.wait_for('message', check=check(ctx.author), timeout=7200)
                txn = txn.content            
            except:
                await dm_user(user_id, "You took too long! Type /join to try again.", discord.Colour.red())
                if user_id in user_ids:
                    user_ids.remove(user_id)
                return

        #insert awaiting txn to db
        await insertAwaitingTxn(username, user_id, txn, addr, amount)

        await dm_user(user_id, "Thanks! Please wait while the txn confirms", discord.Colour.green())
        

###################		Main 		############################
now = datetime.now()
hours, mins = int(now.strftime("%H: %M")[:2]), int(now.strftime("%H: %M")[3:6])

mins += hours * 60

if hours >= 21:
    mins -= 21 * 60
elif hours >= 9:
    mins -= 9 * 60


time_remaining = 720 - mins

if __name__ == "__main__":

    print("min counter: ",mins)

    print_log(str(time_remaining) + " until next resweep.")
    #mins = 0
    init_discord_bot()
    while True:
        sleep(60) # 1 min intervals
        if active:
            mins += 1
            if mins >= 720: # 12 hours
                mins = 0
                discord_client.dispatch("resweep") #send this event to bot every 12 hours
            else:
                discord_client.dispatch("check_pending_tx") #send this event to minute