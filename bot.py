import discord
from discord.ext import commands
from dotenv import load_dotenv
import os


load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")

CUSTOMER_ROLE_ID = int(
    os.getenv("CUSTOMER_ROLE_ID")
)


KEY_FILE = "trial_keys.txt"



intents = discord.Intents.default()
intents.message_content = True
intents.members = True


bot = commands.Bot(
    command_prefix="/",
    intents=intents
)



# -------------------------
# Key system
# -------------------------

def get_keys():

    with open(KEY_FILE, "r") as file:
        return file.readlines()



def claim_key():

    keys = get_keys()


    if len(keys) == 0:
        return None


    key = keys[0].strip()


    with open(KEY_FILE, "w") as file:

        file.writelines(
            keys[1:]
        )


    return key



# -------------------------
# Button
# -------------------------

class TrialButton(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )


    @discord.ui.button(

        label="Claim Free Trial",

        style=discord.ButtonStyle.gray,

        custom_id="trial_button"

    )
    async def claim(

        self,

        interaction,

        button

    ):


        member = interaction.guild.get_member(
            interaction.user.id
        )


        customer_role = interaction.guild.get_role(
            CUSTOMER_ROLE_ID
        )


        # Already claimed check

        if customer_role in member.roles:

            await interaction.response.send_message(

                "❌ You have already claimed a free trial, Or your already a customer.",

                ephemeral=True

            )

            return



        key = claim_key()


        if key is None:

            await interaction.response.send_message(

                "❌ No trial keys left.",

                ephemeral=True

            )

            return



        # Give customer role

        await member.add_roles(
            customer_role
        )



        # DM key

        try:

            await member.send(

                f"""
🎉 Your free trial key:

```{key}```

Your Customer role has also been added.

Enjoy your trial!
"""

            )


        except discord.Forbidden:

            await interaction.response.send_message(

                "❌ Your DMs are closed. Enable DMs and try again.",

                ephemeral=True

            )

            return



        await interaction.response.send_message(

            "✅ Check your DMs! Your trial key has been sent.",

            ephemeral=True

        )



# -------------------------
# Commands
# -------------------------

@bot.command()
async def trial(ctx):

    embed = discord.Embed(

        title="🎁 Free Trial",

        description=
        "Click below to claim your free trial key.\n\n"
        "⚠️ One key per account.",

        colour=0xF2F3F5

    )


    await ctx.send(

        embed=embed,

        view=TrialButton()

    )





@bot.command()
@commands.has_permissions(administrator=True)
async def stock(ctx):

    keys = get_keys()


    await ctx.send(

        f"📦 Trial keys remaining: **{len(keys)}**"

    )



# -------------------------
# Startup
# -------------------------

@bot.event
async def on_ready():

    print(
        f"Logged in as {bot.user}"
    )


    bot.add_view(
        TrialButton()
    )



bot.run(TOKEN)