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

def is_admin_owner():
    async def pred(ctx):
        return ctx.author.id in [339011064660492288, 893124775604543518, 832365411429122109]
    return commands.check(pred)

def is_dm():
    async def pred(ctx):
        return isinstance(ctx.channel, discord.channel.DMChannel)
    return commands.check(pred)

async def dm_user(uid, msg, fields=[], colour=discord.Colour.blue()):
    user = discord_client.get_user(int(uid))

    emb=discord.Embed(description=msg, colour = colour)
    emb.set_author(name="Ada Apocalypse Verification Bot", icon_url=PFP)

    for x in fields:
        emb.add_field(name=str(x[0]), value=str(x[1]), inline=False)

    await user.send(embed=emb)


def print_log(log):
    now = datetime.now()
    current_time = now.strftime("%d/%m/%y %H:%M:%S")
    print(current_time + " - " + log)
    return
################################################################
@discord_client.command()
@is_admin_owner()
async def instructions(ctx):
    emb=discord.Embed(title="How to verify!", description="Please see the commands below to learn how to verify. You will be required to send a specific amount of ADA from YOUR OWN wallet to YOUR OWN wallet to confirm you are the owner.", colour = discord.Colour.blue())
    emb.set_author(name="Ada Apocalypse Verification", icon_url=PFP)
    emb.add_field(name="/join", value="Dm me this command to start the verification process.", inline=True)
    emb.add_field(name="/reset", value="Dm me this command if you are already registered and wish to register a different wallet.", inline=True)
    emb.add_field(name="Unable to send message?", value="Go to -> User Settings -> Privacy -> Allow DM's from server members.", inline=True)
    emb.set_footer(text="Created by Isaac#1277")
    await ctx.channel.send(embed=emb)

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
        await dm_user(user_id, "Incorrect address, check formatting", [], discord.Colour.red())
        
    return False

###################		Check Pending Transactions 		############################

@discord_client.event
async def on_check_pending_tx():
    guild = discord_client.get_guild(SERVER_ID)

    print_log("Checking pending tx's.")

    pendingAddr = []
    pendingAddr = await getAllPendingAddr()

    for a in pendingAddr:
        username = str(a['username'])
        user_id = a['user_id']
        addr = a['addr']
        amount = a['amount']

        txn = checkTxn(addr, amount)
        if txn:
            await updatePendingTxn(addr, amount)

            # testing only
            #addr = 'addr1qy5y697m2us57s7qw5vuwpr39lsnfdqyge7zykxggtgy8hv455ndjyyet3v8ryqs0vgne7hjrvs9k7ee46rrazxp0jvqzu9wf7'
            
            stakeAddr = await getStakeAddr(addr)

            if stakeAddr == "":
                print_log("ERROR: unable to find " + str(a['username']) + " stake addr.")
                await dm_user(user_id, "Unable to find stake addr, please try again.", [],discord.Colour.red())
                return

            if await checkAddrExists(stakeAddr):
                await dm_user(user_id, "ERROR: Address has already been registered", [],discord.Colour.red())
                
                print_log("Error: " + str(username) + " stake addr already registered")
                return

           # search for assets
            assetCount, userWallet = searchAddr(stakeAddr)

            # if no assets are found
            if assetCount == 0:
                print_log(str(username) + " Does not have an Ada Apocalypse")
                await dm_user(user_id, "Could not find the required NFT in your wallet, try again later.", [], discord.Colour.red())
            else:
                member = guild.get_member(user_id)

                if member:
                    roles_aquired = ""
                    
                    for role_idx in ROLE_NAMES:
                        if userWallet[role_idx]:
                            # user is elligible for the role
                            role = discord.utils.get(guild.roles, name=ROLE_NAMES[role_idx])
                            await member.add_roles(role)
                            roles_aquired += ROLE_NAMES[role_idx] +", "


                    #remove , from str
                    roles_aquired = roles_aquired[:len(roles_aquired)-2]

                    await insertMember(user_id, str(username), str(stakeAddr), str(txn), assetCount, userWallet)
                    print_log(str(member.name) + " has " + str(assetCount) + " tokens, Verified")

                    await dm_user(user_id, "You have been verified!",[["Asset Count: ",str(assetCount)],["Roles Aquired:",roles_aquired]], discord.Colour.green())
                    
                else:
                    print_log("Couldn't find member obj for " + str(username))

        else:
            #increment attemtps
            expired_user_id = await checkAttempts(str(a['addr']),a['amount'])
            if expired_user_id:
                await dm_user(expired_user_id, "⚠️⚠️ Address has expired, **DO NOT SEND ADA !!** ⚠️⚠️ Please use /join to try again!",[], discord.Colour.red())
                user_ids.remove(user_id)

###################		Resweep Registered Members 		############################

@discord_client.event
async def on_resweep():
    guild = discord_client.get_guild(SERVER_ID)
    print_log("Initiating resweep.")

    addresses = await get_all_addr()

    for addr in addresses:
        assetCount = await searchAddr(addr['addr'])
        old_asset_count = int(addr['asset_count'])

        
        member = guild.get_member(int(addr['id']))
        if member:
            if assetCount == 0:
                await member.remove_roles(role)
                # remove all active roles

                for name in ROLE_NAMES:
                    if ROLE_NAMES[name].lower() in [x.name.lower() for x in member.roles]:
                        role = discord.utils.get(guild.roles, name=ROLE_NAMES[name])
                        await member.remove_roles(role)


                #x.name.lower() for x in member.roles:
                
                # remove record from DB
                await removeMember(user['addr'])
                print_log(str(user['name']) + " has been removed from the club, address: " + str(user['addr']))
            else:

                for role_idx in ROLE_NAMES:
                    # if user is elligible for role and doesn't already have it => give role
                    if userWallet[role_idx] and ROLE_NAMES[role_idx].lower() not in [x.name.lower() for x in member.roles]: 
                        role = discord.utils.get(guild.roles, name=ROLE_NAMES[role_idx])
                        await member.add_roles(role)
                    # if user is not elligble for role and currenlty has it => remove role
                    elif not userWallet[role_idx] and ROLE_NAMES[role_idx].lower() in [x.name.lower() for x in member.roles]:
                        role = discord.utils.get(guild.roles, name=ROLE_NAMES[role_idx])
                        await member.remove_roles(role)
                
                await updateRoleResweep(user['id'], assetCount, userWallet)

                

###################		DM BOT 		############################
@discord_client.command()
@is_dm()
async def reset(ctx):
    guild = discord_client.get_guild(SERVER_ID)

    user_id = ctx.author.id
    member = guild.get_member(int(user_id))
    username = str(ctx.author.name)

    if user_id in user_ids:
        user_ids.remove(user_id)
    await removeMemberID(user_id)

    for role_idx in ROLE_NAMES:
        # if user is elligible for role and doesn't already have it => give role
        if ROLE_NAMES[role_idx].lower() in [x.name.lower() for x in member.roles]:  
            role = discord.utils.get(guild.roles, name=ROLE_NAMES[role_idx])
            await member.remove_roles(role)

    #await ctx.send('Reset succesfully! Type /join to try again.')
    await dm_user(user_id, "Reset succesful! Type /join to try again.", [], discord.Colour.green())
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

        user = findMember(user_id)
        
        if user:
            url = "https://pool.pm/"+str(user['addr'])
            await dm_user(user_id, "You have already been verified!", [["The wallet currently linked to your account is: ",url], ["/reset","Use this command if you wish to register a new wallet."]])
            user_ids.remove(user_id)
            return

        print_log(username + " has started verification process")
        
        firstMsg = True
        addr = ""

        while not await checkAddrFormat(addr, user_id, firstMsg):
            try:
                firstMsg = False
                # request user addr
                await dm_user(user_id, "Please enter your wallet address: ",[], discord.Colour.blue())
                #await ctx.send()
                addr = await discord_client.wait_for('message', check=check(ctx.author), timeout=120)
                addr = addr.content
                if addr == "/reset":
                    return  
                
            except:
                #await ctx.send('You took too long! Type /join to try again.')
                await dm_user(user_id, "You took too long! Type /join to try again.",[], discord.Colour.red())
                if user_id in user_ids:
                    user_ids.remove(user_id)
                return
        
        #await ctx.send('Addr succesfully captured')

        amount = round(random.uniform(2.000, 3.000),3)

        #await ctx.send('Please send ' + str(amount) + " ADA to your address")
        await dm_user(user_id,'Please send ' + str(amount) + " ADA to your address.",[["Address",str(addr)],["Wen Role?","You will receive your role within 2 minutes of your txn confirming on the blockchain."]] , discord.Colour.blue())

        await insertAwaitingTxn(username, user_id, addr, amount)

        

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