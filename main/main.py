# EggLoL

import discord
import aiohttp
import configparser
import psycopg2
import lxml
import simplejson as json
import numpy as np
from uuid_extensions import uuid7
from psycopg2 import Error
from psycopg2 import IntegrityError
from bs4 import BeautifulSoup
from typing import Optional
from types import SimpleNamespace
from discord import app_commands
from discord.ext import commands

# Read .ini file

cfg = configparser.ConfigParser()

cfg.read("main/keys.ini")

# Connect to PostgreSQL database

try:

    conn = psycopg2.connect(

        host = cfg.get("PostgreSQL", "Host"),
        database = cfg.get("PostgreSQL", "Database"),
        port = cfg.get("PostgreSQL", "Port"),
        user = cfg.get("PostgreSQL", "Username"),
        password = cfg.get("PostgreSQL", "Password")

    )

    conn.autocommit = True

    print("Successfully connected to Postgres server!")

except (Exception, Error) as error:

    print(f"An error occured while trying to connect to PostgreSQL: {error}")

# Synchronous functions

def embed_error(msg):

    return discord.Embed(title = "Error(s)", description = f"{msg}", color = 0xff0000)

def query_mainpulate_data(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            return 200
        
    except:

        return 400
    
def query_get_data(query):

    try:

        with conn.cursor() as cursor:

            cursor.execute(query)

            return cursor.fetchone()
        
    except:

        return 400
    
def get_champions_json(choice):

    with open("main/champions.json") as file:

        champions = json.load(file)

    if choice == 1:

        return list(champions["champions_list"]) + list(champions["champions_for_url"].keys())

    elif choice == 2:

        champions_list = list(champions["champions_list"])
        champions_for_url = champions["champions_for_url"]

        return champions_list, champions_for_url

    elif choice == 3:

        return champions["champions_for_url"]

def lower_list(list_to_lower):

    return list(map(str.lower, list_to_lower))

def is_valid_champion(champion_name):

    all_champions_lowered = lower_list(get_champions_json(1))

    if champion_name.lower() not in all_champions_lowered:

        return False
    
    else:

        return True
    
def get_champion_for_ui(champion_name):

    all_champions = get_champions_json(1)

    all_champions_lowered = lower_list(all_champions)

    champ_index = all_champions_lowered.index(champion_name.lower())

    return all_champions[champ_index]

def get_champion_for_url(champion_name):

    champions_for_url = get_champions_json(3)

    for key, value in champions_for_url.items():

        if key.lower() == champion_name.lower():

            return value
        
    return champion_name

def get_region_for_url(region):

    with open("main/regions.json") as file:

        regions = json.load(file)

    return regions[region]

def create_url(interaction, champion_name, role, rank, queue_type, region):

    if isinstance(region, str):

        region_resp = query_get_data(f"SELECT region FROM discord_user JOIN lol_profile USING (profile_uuid) WHERE discord_user_id = {interaction.user.id}")

        if region_resp != 400:

            region = app_commands.Choice(name = region_resp[0], value = get_region_for_url(region_resp[0]))

        else:

            default_region_json = json.loads(region)

            region = SimpleNamespace(**default_region_json)

    if isinstance(queue_type, str):

        default_queue_json = json.loads(queue_type)

        queue_type = SimpleNamespace(**default_queue_json)

    error_msg = ""

    if queue_type.name == "ARAM" and role != None:

        error_msg += f"* **ARAM** game mode does not have roles!\n"

    if queue_type.name == "ARAM" and rank != '{"name": "Emerald +"}':

        error_msg += f"* **ARAM** game mode does not have ranks!\n"

    if (queue_type.name == "Normal Blind" or queue_type.name == "Normal Draft") and rank != '{"name": "Emerald +"}':

        error_msg += f"* **Normal** game modes do not have ranks!\n"

    if error_msg != "":

        url = None
        champion_name_for_ui = None
        rank = None
        queue_type = None
        region = None

        return url, champion_name_for_ui, rank, queue_type, region, error_msg

    if is_valid_champion(champion_name) == False:

        url = None
        champion_name_for_ui = None
        rank = None
        queue_type = None
        region = None
        error_msg += f"* **{champion_name}** is not a champion in League of Legends.\n"

        return url, champion_name_for_ui, rank, queue_type, region, error_msg

    champion_name_for_url = get_champion_for_url(champion_name)
    champion_name_for_ui = get_champion_for_ui(champion_name)

    if queue_type.name != "ARAM":

        url = f"https://u.gg/lol/champions/{champion_name_for_url}/build"

        if role != None:

            url += f"/{role.value}"

        url += "?"

        if isinstance(rank, str):

            default_rank_json = json.loads(rank)

            rank = SimpleNamespace(**default_rank_json)

        if rank.name != "Emerald +":

            url += f"rank={rank.value}&"

        if queue_type.name != "Ranked Solo/Duo":

            url += f"queueType={queue_type.value}&"

    else:

        url = f"https://u.gg/lol/champions/aram/{champion_name_for_url}-aram?"

    if type(region) != SimpleNamespace:

        url += f"region={region.value}&"

    return url, champion_name_for_ui, rank, queue_type, region, error_msg

def edit_skill_path_grid(div, skill_path_grid, row_index):

    row_mapping = {

        0: "<:q_:1142021169961259038>",
        1: "<:w_:1142021171278250064>",
        2: "<:e_:1142021173253779526>",
        3: "<:r_:1142021174415605811>" 

    }

    if "skill-up" in div["class"]:

        skill_path_grid += row_mapping[row_index]

    else: 

        skill_path_grid += "<:gs:1142000576721322077>"

    return skill_path_grid
    
# Asynchronous functions

async def aio_get_soup(url):

    async with aiohttp.ClientSession(headers = {"User-Agent": "Mozilla/5.0"}) as session:

        async with session.get(url = url) as response:

            resp = await response.text()

            return BeautifulSoup(resp, "lxml")
        

# Bot initialization

TOKEN = cfg.get("Discord", "BotToken")

bot = commands.Bot(command_prefix = ".", intents = discord.Intents.all())

# Bot

@bot.event
async def on_ready():

    try:
        
        synced = await bot.tree.sync()
        print(f"Succesfully synced {len(synced)} command(s)!")

    except Exception as e:

        print(e)

    print(f"{bot.user.name} is online!")

    await bot.change_presence(status = discord.Status.online, activity= discord.Game("/help"))

@bot.tree.command(name = "help", description = "Get an overview of all the commands and how to use them.")
async def help(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral = False)
    #

    embed = discord.Embed(title = "Test", color = 0xE8E1E1)

    #
    await interaction.followup.send(embed = embed, ephemeral = False)
    return

@bot.tree.command(name = "set_profile", description = "For a more tailored experience, set up your LoL profile!")
@app_commands.describe(region = "Your matchmaking region.", username = "Your LoL username.", main_champion = "Your main champion (if you don't main one champion, put your most played champion)")
@app_commands.choices(region = [

    app_commands.Choice(name = "NA", value = "NA"),
    app_commands.Choice(name = "EUW", value = "EUW"),
    app_commands.Choice(name = "KR", value = "KR"),
    app_commands.Choice(name = "BR", value = "BR"),
    app_commands.Choice(name = "EUN", value = "EUN"),
    app_commands.Choice(name = "JP", value = "JP"),
    app_commands.Choice(name = "LAN", value = "LAN"),
    app_commands.Choice(name = "LAS", value = "LAS"),
    app_commands.Choice(name = "OCE", value = "OCE"),
    app_commands.Choice(name = "RU", value = "RU"),
    app_commands.Choice(name = "TR", value = "TR"),
    app_commands.Choice(name = "PH", value = "PH"),
    app_commands.Choice(name = "SG", value = "SG"),
    app_commands.Choice(name = "TH", value = "TH"),
    app_commands.Choice(name = "TW", value = "TW"),
    app_commands.Choice(name = "VN", value = "VN")

])

async def set_profile(interaction: discord.Interaction, region: app_commands.Choice[str], username: app_commands.Range[str, 3, 16], main_champion: app_commands.Range[str, 3, 14]):

    await interaction.response.defer(ephemeral = False)
    #

    region = region.value

    with open("main/regions.json") as file:

        regions = json.load(file)

    user_url = f"https://u.gg/lol/profile/{regions[region]}/{username}/overview"

    profile_soup = await aio_get_soup(user_url)

    error_msg = ""

    try:

        username_char_corrected = profile_soup.find("div", "summoner-name").text

    except AttributeError:

        error_msg += f"* The username **{username}** was not found in the **{region}** region. *Try another region or double-check the username*.\n"

    if is_valid_champion(main_champion) == False:

        error_msg += f"* **{main_champion}** is not a champion in League of Legends.\n"

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))
        return
    
    # Checkpoint | username and main_champion have been verified 

    rank = profile_soup.find("span", "unranked").text
    lp = ""

    if rank  == "":

        rank = profile_soup.find("div", "rank-text").span.text
        lp = profile_soup.find("div", "rank-text").find_all("span")[1].text

    # Checkpoint | rank has been retrieved

    main_champion_for_ui = get_champion_for_ui(main_champion)
    main_champion_for_db = main_champion_for_ui.replace("'", '"')

    # Checkpoint | main_champion has been character corrected

    uuid = uuid7()
    discord_user_id = interaction.user.id

    initial_query_resp = query_mainpulate_data(f"INSERT INTO discord_user (discord_user_id) VALUES ({discord_user_id});")

    if initial_query_resp == 400:

        try:

            profile_uuid = query_get_data(f"SELECT profile_uuid FROM discord_user WHERE discord_user_id = {discord_user_id}")[0]
            lol_profile_data = query_get_data(f"SELECT region, username, main_champion, rank FROM lol_profile WHERE profile_uuid = '{profile_uuid}'")

        except:

            await interaction.followup.send(embed = embed_error("* Something went wrong while updating your profile. Try again later."))
            return

        enetered_data_tuple = (region, username_char_corrected, main_champion_for_db, f"{rank} {lp}")

        if enetered_data_tuple == lol_profile_data:

            embed = discord.Embed(title = "Your current profile already matches what you entered...", color = 0xFFA63B)
            await interaction.followup.send(embed = embed)
            return

        query_mainpulate_data(f"UPDATE lol_profile SET region = '{region}', username = '{username_char_corrected}', main_champion = '{main_champion_for_db}', rank = '{rank} {lp}' WHERE profile_uuid = '{profile_uuid}';")

        embed = discord.Embed(title = "Profile has been updated!", description = f"__Your new profile__:\n\n**Region**: {region}\n**Username**: {username_char_corrected}\n**Main Champion**: {main_champion_for_ui}\n**Rank**: {rank} {lp}", color = 0x00AA00)
        await interaction.followup.send(embed = embed)
        return

    query_mainpulate_data(f"INSERT INTO lol_profile (profile_uuid, region, username, main_champion, rank) VALUES ('{uuid}', '{region}', '{username_char_corrected}', '{main_champion_for_db}', '{rank} {lp}');")
    query_mainpulate_data(f"UPDATE discord_user SET profile_uuid = '{uuid}' WHERE discord_user_id = {discord_user_id}")

    #
    
    embed = discord.Embed(title = "Profile has been created!", description = f"__Your new profile__:\n\n**Region**: {region}\n**Username**: {username_char_corrected}\n**Main Champion**: {main_champion_for_ui}\n**Rank**: {rank} {lp}", color = 0x00AA00)
    await interaction.followup.send(embed = embed)
    return

@bot.tree.command(name = "overview", description = "Get an overview of the champion in your specific rank, region and role!")
@app_commands.describe(champion_name = "Champion to get overview for")
@app_commands.choices(
    
    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "ARAM", value = "aram"),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),
        app_commands.Choice(name = "Normal Blind", value = "normal_blind_5x5"),
        app_commands.Choice(name = "Normal Draft", value = "normal_draft_5x5")

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)

async def overview(interaction: discord.Interaction, champion_name: str, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    url, champion_name_for_ui, rank, queue_type, region, error_msg = create_url(interaction, champion_name, role, rank, queue_type, region)

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))

    soup = await aio_get_soup(url)

    try:

        tier = soup.find("div", "champion-tier").div.text
        win_rate = soup.find("div", "win-rate").div.text
        overall_rank = soup.find("div", "overall-rank").div.text
        pick_rate = soup.find("div", "pick-rate").div.text
        ban_rate = soup.find("div", "ban-rate").div.text
        total_matches = soup.find("div", "matches").div.text
        if queue_type.name != "ARAM":
        
            role = soup.find("div", "role-value").div.text
    
    except AttributeError:

        await interaction.followup.send(embed = embed_error(f"* No data was found for {champion_name_for_ui}!"))
        return

    if queue_type.name != "ARAM":

        embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**\n{rank.name}", color = 0x222247)

    else:
        
        embed = discord.Embed(title = f"{champion_name_for_ui}", description = f"**{queue_type.name}** in **{region.name}**", color = 0x222247)

    embed.add_field(name = "Tier", value =  f"{tier}")
    embed.add_field(name = "Win Rate", value =  f"{win_rate}")
    embed.add_field(name = "Position", value =  f"{overall_rank}")
    embed.add_field(name = "Pick Rate", value =  f"{pick_rate}")
    embed.add_field(name = "Ban Rate", value =  f"{ban_rate}")
    embed.add_field(name = "Matches", value =  f"{total_matches}")

    await interaction.followup.send(embed = embed)
    return

@bot.tree.command(name = "build", description = "Get the complete build for the champion including the runes, summoner spells, items and more.")
@app_commands.describe(champion_name = "Champion to get build for")
@app_commands.choices(
    
    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "ARAM", value = "aram"),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),
        app_commands.Choice(name = "Normal Blind", value = "normal_blind_5x5"),
        app_commands.Choice(name = "Normal Draft", value = "normal_draft_5x5")

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)

async def build(interaction: discord.Interaction, champion_name: str, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    url, champion_name_for_ui, rank, queue_type, region, error_msg = create_url(interaction, champion_name, role, rank, queue_type, region)

    if error_msg != "":

        await interaction.followup.send(embed = embed_error(error_msg))

    soup = await aio_get_soup(url)

    try:

        runes_div = soup.find("div", "recommended-build_runes")
        runes = runes_div.find("div", "rune-trees-container-2 media-query media-query_MOBILE_LARGE__DESKTOP_LARGE").find_all("div", "perk-active")
        shards = runes_div.find("div", "rune-trees-container-2 media-query media-query_MOBILE_LARGE__DESKTOP_LARGE").find_all("div", "shard-active")
        runes_wr = runes_div.find("span", "win-rate").text
        runes_matches = runes_div .find("span", "matches").text

    except AttributeError:

        await interaction.followup.send(embed = embed_error(f"* No data was found for {champion_name_for_ui}!"))
        return

    summoner_spells_div = soup.find("div", "summoner-spells")
    summoner_spells = summoner_spells_div.find_all("div", recursive = False)[1].find_all("img")
    summoner_spells_wr = summoner_spells_div.find("span", "win-rate").text
    summoner_spells_matches = summoner_spells_div.find("span", "matches").text

    skill_priority_div = soup.find("div", "skill-priority_content")
    skill_priority = skill_priority_div.find("div", "skill-priority-path").find_all("div", "skill-label")

    try:

        skill_priority_wr = skill_priority_div.find("div", "winrate").span.text
        skill_priority_matches = skill_priority_div.find("div", "matches").text

    except:

        skill_priority_wr = "~%"
        skill_priority_matches = "~ Matches"

    skill_path = soup.find("div", "skill-path-container")
    skill_path_rows = skill_path.find_all("div", "skill-order")[:4]

    if queue_type.name != "ARAM":

        role = soup.find("div", "role-value").div.text

        if queue_type.name == "Ranked Solo/Duo" or queue_type.name == "Ranked Flex":

            embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**\n{rank.name}", color = 0x222247)

        else:

            embed = discord.Embed(title = f"{champion_name_for_ui} | {role}", description = f"**{queue_type.name}** in **{region.name}**", color = 0x222247)

    else:
        
        embed = discord.Embed(title = f"{champion_name_for_ui}", description = f"**{queue_type.name}** in **{region.name}**", color = 0x222247)

    runes_text = ""

    for rune in runes:

        runes_text += rune.img["alt"] + "\n"

    for shard in shards:

        runes_text += shard.img["alt"] + "\n"
    
    summoner_spell_text = ""

    for summoner_spell in summoner_spells:

        summoner_spell_text += summoner_spell["alt"] + "\n"

    skill_priority_mapping = {

        "Q": "<:q_:1142021169961259038>",
        "W": "<:w_:1142021171278250064>",
        "E": "<:e_:1142021173253779526>"

    }

    embed.add_field(name = f"Runes | {runes_wr}{runes_matches}", value = f"{runes_text}")
    embed.add_field(name = f"Summoner Spells | {summoner_spells_wr}{summoner_spells_matches}", value = f"{summoner_spell_text}")
    embed.add_field(name = f"Skill Priority | {skill_priority_wr} WR ({skill_priority_matches})", value = f"{skill_priority_mapping[skill_priority[0].text]} > {skill_priority_mapping[skill_priority[1].text]} > {skill_priority_mapping[skill_priority[2].text]}", inline = False)
    embed.add_field(name = "Skill Path", value = "", inline = False)
    embed.add_field(name = "", value = "<:1_:1142013758198251528><:2_:1142014838734856276><:3_:1142014837010993172><:4_:1142014822335139893><:5_:1142014801162281001><:6_:1142014789279809559><:7_:1142014755389845575><:8_:1142014739065618462><:9_:1142015195632386109><:10:1142015179765321781><:11:1142015164749729823><:12:1142015156587614259><:13:1142015154989580311><:14:1142015150661062698><:15:1142015148056387634><:16:1142015131912503358><:17:1142015121154121779><:18:1142015119560282192>", inline = False)

    skill_path_grid = ""

    for row_index, row in enumerate(skill_path_rows):

        for div in row:

            skill_path_grid = edit_skill_path_grid(div, skill_path_grid, row_index)

        skill_path_grid += "\n"
        embed.add_field(name = "", value = f"{skill_path_grid}", inline = False)
        skill_path_grid = ""

    await interaction.followup.send(embed = embed)
    return

@bot.tree.command(name = "vs", description = "Get the complete build and WR for your champion vs. another champion!")
@app_commands.describe(first_champion = "main_champion vs. first_champion OR first_champion vs. second_champion", second_champion = "first_champion vs. second_champion")
@app_commands.choices(
    
    role = [
    
        app_commands.Choice(name = "Top", value = "top"),
        app_commands.Choice(name = "Jungle", value = "jungle"),
        app_commands.Choice(name = "Middle", value = "mid"),
        app_commands.Choice(name = "Bot/ADC", value = "adc"),
        app_commands.Choice(name = "Support", value = "support")

    ],
    rank = [

        app_commands.Choice(name = "Platinum +", value = "platinum_plus"),
        app_commands.Choice(name = "Emerald +", value = "emerald_plus"),
        app_commands.Choice(name = "Diamond +", value = "diamond_plus"),
        app_commands.Choice(name = "Diamond 2 +", value = "diamond_2_plus"),
        app_commands.Choice(name = "Master +", value = "master_plus"),
        app_commands.Choice(name = "All Ranks", value = "overall"),
        app_commands.Choice(name = "Challenger", value = "challenger"),
        app_commands.Choice(name = "Grandmaster", value = "grandmaster"),
        app_commands.Choice(name = "Master", value = "master"),
        app_commands.Choice(name = "Diamond", value = "diamond"),
        app_commands.Choice(name = "Emerald", value = "emerald"),
        app_commands.Choice(name = "Platinum", value = "platinum"),
        app_commands.Choice(name = "Gold", value = "gold"),
        app_commands.Choice(name = "Silver", value = "silver"),
        app_commands.Choice(name = "Bronze", value = "bronze"),
        app_commands.Choice(name = "Iron", value = "iron")

    ],
    queue_type = [

        app_commands.Choice(name = "Ranked Solo/Duo", value = ""),
        app_commands.Choice(name = "ARAM", value = "aram"),
        app_commands.Choice(name = "Ranked Flex", value = "ranked_flex_sr"),
        app_commands.Choice(name = "Normal Blind", value = "normal_blind_5x5"),
        app_commands.Choice(name = "Normal Draft", value = "normal_draft_5x5")

    ],
    region = [

        app_commands.Choice(name = "World", value = "world"),
        app_commands.Choice(name = "NA", value = "na1"),
        app_commands.Choice(name = "EUW", value = "euw1"),
        app_commands.Choice(name = "KR", value = "kr"),
        app_commands.Choice(name = "BR", value = "br1"),
        app_commands.Choice(name = "EUN", value = "eun1"),
        app_commands.Choice(name = "JP", value = "jp1"),
        app_commands.Choice(name = "LAN", value = "la1"),
        app_commands.Choice(name = "LAS", value = "la2"),
        app_commands.Choice(name = "OCE", value = "oc1"),
        app_commands.Choice(name = "RU", value = "ru"),
        app_commands.Choice(name = "TR", value = "tr1"),
        app_commands.Choice(name = "PH", value = "ph1"),
        app_commands.Choice(name = "SG", value = "sg2"),
        app_commands.Choice(name = "TH", value = "th2"),
        app_commands.Choice(name = "TW", value = "tw2"),
        app_commands.Choice(name = "VN", value = "vn2")

    ]
)
async def vs(interaction: discord.Interaction, first_champion: str, second_champion: Optional[str] = None, role: Optional[app_commands.Choice[str]] = None, rank: Optional[app_commands.Choice[str]] = '{"name": "Emerald +"}',  queue_type: Optional[app_commands.Choice[str]] = '{"name": "Ranked Solo/Duo"}', region: Optional[app_commands.Choice[str]] = '{"name": "World", "value": "World"}'):

    await interaction.response.defer(ephemeral = False)

    if second_champion == None:

        if is_valid_champion(first_champion) == False:

            await interaction.followup.send(embed = embed_error(f"* **{first_champion}** is not a champion in League of Legends.\n"))
            return

        my_champ = query_get_data(f"SELECT main_champion FROM discord_user JOIN lol_profile USING (profile_uuid) WHERE discord_user_id = {interaction.user.id};")

        if my_champ == None:

            await interaction.followup.send(embed = embed_error(f"* It appears that you have not set up your profile! If you would like to, use /set_profile. If you would like to use this function without setting up your profile, specify 'second_champion' when calling this function."))
            return

        opp = first_champion
        
    else:

        error_msg = ""

        if is_valid_champion(first_champion) == False:

            error_msg += f"* **{first_champion}** is not a champion in League of Legends.\n"

        if is_valid_champion(second_champion) == False:

            error_msg += f"* **{second_champion}** is not a champion in League of Legends.\n"

        if error_msg != "":

            await interaction.followup.send(embed = embed_error(error_msg))
            return
        
        my_champ = first_champion
        opp = second_champion

    # Checkpoint | 'my_champ' and 'opp' have been verified and assigned

    url, champion_name_for_ui, rank, queue_type, region, error_msg = create_url(interaction, my_champ, role, rank, queue_type, region)

    url += f"opp={opp}"

    soup = await aio_get_soup(url)

    embed = discord.Embed(title = "h", description = "n", color = 0xD13441)

    await interaction.followup.send(embed = embed)
    return

@bot.tree.command(name = "profile", description = "Retrieve your profile data from our database or search for someone else's!")
async def profile(interaction: discord.Interaction):


    await interaction.response.defer(ephemeral=False)

    # Retrieve user's profile from the database
    discord_profile = interaction.user.id

    if discord_profile is None:

        await interaction.followup.send("You don't have a profile. Create one using /set_profile!", ephemeral=True)
        
    else:

        # Construct and send the embed with profile information
        #embed = discord.Embed(title=f"LVL {user_profile['level']} - {interaction.user.display_name}")
        #embed.set_thumbnail(url=user_profile['lol_profile_picture'])
        #embed.add_field(name="Rank", value=f"{user_profile['rank_name']} - {user_profile['lp']} LP")
        #embed.add_field(name="Win/Loss", value=f"{user_profile['win']}W/{user_profile['loss']}L")

        #await interaction.followup.send(embed=embed, ephemeral=False)

        return
    
bot.run(TOKEN)