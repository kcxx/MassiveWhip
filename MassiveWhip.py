# -*- coding: utf-8 -*-
"""
Created on Mon Oct 12 16:00:22 2020

@author: kachnicka
"""

import os
import discord
import random
import aiohttp

from dotenv import load_dotenv
from datetime import datetime
from tabulate import tabulate


class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, command_prefix='/')
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER = os.getenv('OWNER_ID')
GUILD = discord.Object(id=os.getenv('GUILD_ID'))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = MyClient(intents=intents)


@client.event
async def on_ready():
    await client.get_user(int(OWNER)).send('I am ready')


def is_vedeni():
    def predicate(interaction: discord.Interaction) -> bool:
        role = discord.utils.get(interaction.guild.roles, name='vedeni')
        return role in interaction.user.roles

    return discord.app_commands.check(predicate)


def log_command(command, author):
    print(datetime.now(), command, '\t', author)


def list_diff(li1, li2):
    return list(list(set(li1) - set(li2)) + list(set(li2) - set(li1)))


def list_subtract(li1, li2):
    return list(list(set(li1) - set(li2)))


@client.tree.context_menu(name='Whip')
@is_vedeni()
async def whip(interaction: discord.Interaction, message: discord.Message):
    log_command('whip', interaction.user.name)

    async with interaction.channel.typing():
        url = f'https://raid-helper.dev/api/v2/events/{message.id}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    return await interaction.response.send_message(f'Raid-Helper server error.', ephemeral=True)

                js = await r.json()
                if 'status' in js and js['status'] == 'failed':
                    return await interaction.response.send_message(f'Raid-Helper event [{message.id}] not found.',
                                                                   ephemeral=True)

                all_raiders = discord.utils.get(interaction.guild.roles, name='raider').members
                all_raiders.extend(discord.utils.get(interaction.guild.roles, name='vedeni').members)
                all_raiders = list(set(all_raiders))

                signed_raiders = [m['name'] for m in js['signUps']]
                unsigned_raiders = [r for r in all_raiders if r.display_name not in signed_raiders]

                mention = True
                if not unsigned_raiders:
                    msg = ['You\'ll call me back. I know it.']
                else:
                    msg = ['Finally, a chance to demonstrate my... talents...\n']
                    for ur in unsigned_raiders:
                        msg.extend([ur.mention if mention else ur.display_name, ' '])
                    msg.extend(['\nShall we begin?'])

                await interaction.response.send_message(''.join(msg))


councilRoleSize = 7
councilVedeniCount = 3
councilCoreCount = 2


@client.tree.command(name='council',
                     description='Generate new loot council based on the discord roles (vedeni/raider).')
@is_vedeni()
async def council(interaction: discord.Interaction):
    log_command('council', interaction.user.name)
    async with interaction.channel.typing():
        vedeni = discord.utils.get(interaction.guild.roles, name='vedeni').members
        core = list_subtract(discord.utils.get(interaction.guild.roles, name='raider').members, vedeni)

        c_vedeni = random.sample(vedeni, k=councilRoleSize)
        c_vedeni = [m.display_name for m in c_vedeni]
        c_vedeni = c_vedeni[:councilVedeniCount] + [''] + c_vedeni[councilVedeniCount:]

        c_core = random.sample(core, k=councilRoleSize - 1)
        c_core = [m.display_name for m in c_core]
        c_core = c_core[:councilCoreCount] + ['', ''] + c_core[councilCoreCount:]

        new_council = list(zip(c_vedeni, c_core))
        table = tabulate(new_council, headers=["Vedeni", "CoreRaiders"])
        msg = ''.join(['```New loot council \n\n', table, '```'])

        await interaction.response.send_message(msg)


client.run(TOKEN)
