# -*- coding: utf-8 -*-
"""
Created on Mon Oct 12 16:00:22 2020

@author: kachnicka
"""

import os
import discord
import random

from dotenv import load_dotenv
from datetime import datetime, timedelta
from discord.ext import commands
from tabulate import tabulate

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = os.getenv('OWNER_ID')

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

signedReactions = ['Warrior', 'Druid', 'Paladin', 'Rogue', 'Hunter', 'Mage', 'Warlock', 'Priest', 'Shaman', 'Bench',
                   'Late', 'Tentative', 'Absence']
councilRoleSize = 7
councilVedeniCount = 3
councilCoreCount = 2


@bot.event
async def on_ready():
    await bot.get_user(int(OWNER)).send('I am ready')


def is_eligible_to_whip():
    async def predicate(ctx):
        vedeniRole = await commands.RoleConverter().convert(ctx, 'vedeni')
        return vedeniRole in ctx.author.roles

    return commands.check(predicate)


def parse_raidhelper_event_datetime(embedFields):
    date = embedFields[0].value.split('&dates=', 1)[1].split('T', 1)[0]
    time = embedFields[1].value.split('**[', 1)[1].split(' ', 1)[0]
    return datetime.strptime(date + time, '%Y%m%d%H:%M')


def is_upcoming_event(msg):
    return datetime.utcnow() < parse_raidhelper_event_datetime(msg.embeds[0].fields)


async def getUnsignedMembers(ctx):
    vedeniRole = await commands.RoleConverter().convert(ctx, 'vedeni')
    raiderRole = await commands.RoleConverter().convert(ctx, 'raider')
    # clenRole = await commands.RoleConverter().convert(ctx, 'clen')
    allRaiders = set(vedeniRole.members + raiderRole.members)
    unsignedRaiders = set()

    async for msg in ctx.channel.history(limit=10):
        if msg.author.name == 'Raid-Helper' and is_upcoming_event(msg):
            signedUsersSet = set()
            for r in msg.reactions:
                if r.emoji.name in signedReactions:
                    signedUsersSet.update(set(await r.users().flatten()))

            signedRaidersSet = set()
            for u in signedUsersSet:
                signedMember = ctx.guild.get_member(u.id)
                if vedeniRole in signedMember.roles or raiderRole in signedMember.roles:
                    signedRaidersSet.add(signedMember)

            unsignedRaiders.update(allRaiders.difference(signedRaidersSet))

    return unsignedRaiders


async def getUnsignedMembersMsg(ctx, mention=True):
    unsignedRaiders = await getUnsignedMembers(ctx)
    if not unsignedRaiders:
        msg = ['Try not to miss me too much.']
    else:
        msg = ['Hmmm, you\'re in trouble now:\n']
    for ur in unsignedRaiders:
        msg.extend([ur.mention if mention else ur.display_name, ' '])

    return ''.join(msg)


@bot.command(name='whipHere', help='Whip lash all unsigned members in this channel\'s recent events.')
@is_eligible_to_whip()
async def whipHere(ctx):
    await ctx.message.delete()
    async with ctx.channel.typing():
        msg = await getUnsignedMembersMsg(ctx)
        print('Zabicoval: ', ctx.author.name)
        await ctx.send(msg)


@bot.command(name='whipHereTest', help='Whip lash all unsigned members in this channel\'s recent events. Sent as DM.')
@is_eligible_to_whip()
async def whipHereTest(ctx):
    await ctx.message.delete()
    async with ctx.channel.typing():
        msg = await getUnsignedMembersMsg(ctx, mention=False)
        print('Zabicoval: ', ctx.author.name)
        await ctx.author.send(msg)


@whipHere.error
async def whipHere_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.message.delete()


@bot.command(name='t', help='test')
async def t(ctx):
    await ctx.send('I am here.')


def ListDiff(li1, li2):
    return list(list(set(li1) - set(li2)) + list(set(li2) - set(li1)))


def ListSubtract(li1, li2):
    return list(list(set(li1) - set(li2)))


@bot.command(name='newCouncil', help='Generate new loot council based on discord ranks.')
@is_eligible_to_whip()
async def newCouncil(ctx):
    async with ctx.channel.typing():
        vedeni = (await commands.RoleConverter().convert(ctx, 'vedeni')).members
        core = ListSubtract((await commands.RoleConverter().convert(ctx, 'raider')).members, vedeni)

        cVedeni = random.sample(vedeni, k=councilRoleSize)
        cCore = random.sample(core, k=councilRoleSize - 1)
        cVedeni = [cVedeni[n].display_name for n in range(len(cVedeni))]
        cCore = [cCore[n].display_name for n in range(len(cCore))]
        cVedeni = cVedeni[:councilVedeniCount] + [''] + cVedeni[councilVedeniCount:]
        cCore = cCore[:councilCoreCount] + ['', ''] + cCore[councilCoreCount:]

        council = [[cVedeni[n], cCore[n]] for n in range(len(cVedeni))]
        table = tabulate(council, headers=["Vedeni", "CoreRaiders"])
        msg = ''.join(['```New loot council \n\n', table, '```'])

        await ctx.message.delete()
        await ctx.send(msg)


bot.run(TOKEN)
#    bot.send_message(bot.get_user(OWNER), 'I am dead')
