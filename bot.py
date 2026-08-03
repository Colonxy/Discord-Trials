import discord
from discord.ext import commands
from discord import app_commands

from dotenv import load_dotenv
import os


load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")

GEN_ACCESS_ROLE_ID = int(
    os.getenv("GEN_ACCESS_ROLE_ID")
)


# Key files

KEY_FILES = {

    "day": "day_keys.txt",

    "week": "week_keys.txt",

    "month": "month_keys.txt",

    "lifetime": "lifetime_keys.txt"

}



# Discord intents

intents = discord.Intents.default()

intents.members = True


bot = commands.Bot(

    command_prefix="!",

    intents=intents

)



# ==========================
# KEY SYSTEM
# ==========================


def get_key(filename):

    try:

        with open(filename, "r") as file:

            keys = file.readlines()


        if len(keys) == 0:

            return None



        key = keys[0].strip()



        with open(filename, "w") as file:

            file.writelines(
                keys[1:]
            )


        return key



    except FileNotFoundError:

        print(
            f"{filename} not found"
        )

        return None





async def send_key(

    interaction: discord.Interaction,

    key_type: str

):


    # Check role

    role = interaction.guild.get_role(

        GEN_ACCESS_ROLE_ID

    )


    if role not in interaction.user.roles:


        await interaction.response.send_message(

            "❌ You need the **Gen Access** role to use this.",

            ephemeral=True

        )

        return



    key = get_key(

        KEY_FILES[key_type]

    )


    if key is None:


        await interaction.response.send_message(

            "❌ No keys available for this product.",

            ephemeral=True

        )

        return



    try:


        await interaction.user.send(

            f"""
✅ Your {key_type.title()} key:
{key}


Enjoy!
"""

        )


        await interaction.response.send_message(

            "✅ Check your DMs! Your key has been sent.",

            ephemeral=True

        )



    except discord.Forbidden:


        await interaction.response.send_message(

            "❌ I cannot DM you. Please enable DMs from server members.",

            ephemeral=True

        )





# ==========================
# SLASH COMMANDS
# ==========================


@bot.tree.command(
    name="day",
    description="Get a day key"
)

async def day(
    interaction: discord.Interaction
):

    await send_key(

        interaction,

        "day"

    )





@bot.tree.command(
    name="week",
    description="Get a week key"
)

async def week(
    interaction: discord.Interaction
):

    await send_key(

        interaction,

        "week"

    )





@bot.tree.command(
    name="month",
    description="Get a month key"
)

async def month(
    interaction: discord.Interaction
):

    await send_key(

        interaction,

        "month"

    )





@bot.tree.command(
    name="lifetime",
    description="Get a lifetime key"
)

async def lifetime(
    interaction: discord.Interaction
):

    await send_key(

        interaction,

        "lifetime"

    )





# ==========================
# READY
# ==========================


@bot.event

async def on_ready():


    await bot.tree.sync()


    print(

        f"Logged in as {bot.user}"

    )



bot.run(TOKEN)