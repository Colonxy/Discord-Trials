import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

try:
    GUILD_ID = int(os.getenv("GUILD_ID", "0"))
    CUSTOMER_ROLE_ID = int(os.getenv("CUSTOMER_ROLE_ID", "0"))
except ValueError:
    raise ValueError(
        "GUILD_ID and CUSTOMER_ROLE_ID must be numbers."
    )


# ============================================================
# CHECK INVOICE FORMAT
# ============================================================

def is_valid_invoice_format(invoice_id: str) -> bool:

    # Example:
    # 26e0f061-f08d-4551-8fca-0ec0a4769dc6

    pattern = (
        r"^[0-9a-fA-F]{8}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}$"
    )

    return bool(
        re.fullmatch(
            pattern,
            invoice_id
        )
    )


# ============================================================
# CLAIM CUSTOMER BUTTON
# ============================================================

class ClaimCustomerButton(discord.ui.Button):

    def __init__(self):

        super().__init__(
            label="Claim Customer Role",
            style=discord.ButtonStyle.secondary,
            emoji="🛒",
            custom_id="claim_customer_role"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_modal(
            InvoiceModal()
        )


# ============================================================
# PERSISTENT VIEW
# ============================================================

class VerificationView(discord.ui.View):

    def __init__(self):

        # Makes the button survive bot restarts
        super().__init__(
            timeout=None
        )

        self.add_item(
            ClaimCustomerButton()
        )


# ============================================================
# INVOICE MODAL
# ============================================================

class InvoiceModal(discord.ui.Modal):

    def __init__(self):

        super().__init__(
            title="Claim Customer Role"
        )

        self.invoice_id = discord.ui.TextInput(
            label="Invoice ID",
            placeholder=(
                "26e0f061-f08d-4551-8fca-0ec0a4769dc6"
            ),
            required=True,
            min_length=36,
            max_length=36
        )

        self.add_item(
            self.invoice_id
        )


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        # ====================================================
        # GET INVOICE ID
        # ====================================================

        invoice_id = (
            self.invoice_id.value
            .strip()
            .replace("**", "")
            .strip()
        )


        # ====================================================
        # CHECK INVOICE FORMAT
        # ====================================================

        if not is_valid_invoice_format(
            invoice_id
        ):

            embed = discord.Embed(
                title="❌ Invalid Invoice ID",
                description=(
                    "The invoice ID you entered doesn't "
                    "have the correct format.\n\n"
                    "Please enter the complete invoice ID."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # CHECK SERVER
        # ====================================================

        guild = interaction.guild

        if guild is None:

            await interaction.response.send_message(
                "❌ This can only be used inside the server.",
                ephemeral=True
            )

            return


        # ====================================================
        # GET CUSTOMER ROLE
        # ====================================================

        role = guild.get_role(
            CUSTOMER_ROLE_ID
        )

        if role is None:

            embed = discord.Embed(
                title="❌ Configuration Error",
                description=(
                    "I couldn't find the Customer role.\n\n"
                    "Check your CUSTOMER_ROLE_ID "
                    "Railway variable."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # FETCH MEMBER DIRECTLY FROM DISCORD
        # ====================================================

        try:

            member = await guild.fetch_member(
                interaction.user.id
            )

        except discord.NotFound:

            await interaction.response.send_message(
                "❌ You are not a member of this server.",
                ephemeral=True
            )

            return

        except discord.Forbidden:

            await interaction.response.send_message(
                (
                    "❌ I don't have permission to retrieve "
                    "your server membership."
                ),
                ephemeral=True
            )

            return

        except discord.HTTPException as error:

            print(
                f"Member fetch error: {error}"
            )

            await interaction.response.send_message(
                (
                    "❌ Discord couldn't retrieve your "
                    "server profile. Please try again."
                ),
                ephemeral=True
            )

            return


        # ====================================================
        # CHECK IF ALREADY HAS CUSTOMER ROLE
        # ====================================================

        if role in member.roles:

            embed = discord.Embed(
                title="✅ Already Verified",
                description=(
                    "You already have the **Customer** role."
                ),
                color=discord.Color.green()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # CHECK BOT CAN MANAGE THE ROLE
        # ====================================================

        if guild.me is None:

            await interaction.response.send_message(
                "❌ I couldn't retrieve my bot member.",
                ephemeral=True
            )

            return


        if role >= guild.me.top_role:

            embed = discord.Embed(
                title="❌ Role Permission Error",
                description=(
                    "I can't give the Customer role because "
                    "my bot role isn't high enough.\n\n"
                    "Go to **Server Settings → Roles** and "
                    "move the bot's role **above** the "
                    "**Customer** role."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # GIVE CUSTOMER ROLE
        # ====================================================

        try:

            await member.add_roles(
                role,
                reason=(
                    "Customer verification | "
                    f"Invoice: {invoice_id}"
                )
            )

        except discord.Forbidden:

            embed = discord.Embed(
                title="❌ Permission Error",
                description=(
                    "Discord didn't allow me to give you "
                    "the Customer role.\n\n"
                    "Make sure the bot's highest role is "
                    "above the Customer role."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        except discord.HTTPException as error:

            print(
                f"Role assignment error: {error}"
            )

            embed = discord.Embed(
                title="❌ Discord Error",
                description=(
                    "Discord couldn't give you the "
                    "Customer role.\n\n"
                    "Please try again."
                ),
                color=discord.Color.red()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # SUCCESS
        # ====================================================

        embed = discord.Embed(
            title="✅ Verification Successful",
            description=(
                "Your invoice ID was accepted!\n\n"
                "You have been given the "
                "**Customer** role."
            ),
            color=discord.Color.green()
        )

        embed.add_field(
            name="Invoice ID",
            value=f"`{invoice_id}`",
            inline=False
        )

        embed.set_footer(
            text="Customer Verification"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# BOT
# ============================================================

class VerificationBot(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )


    async def setup_hook(self):

        guild = discord.Object(
            id=GUILD_ID
        )

        # ====================================================
        # SYNC SLASH COMMANDS
        # ====================================================

        self.tree.copy_global_to(
            guild=guild
        )

        await self.tree.sync(
            guild=guild
        )

        # ====================================================
        # REGISTER PERSISTENT BUTTON
        # ====================================================

        self.add_view(
            VerificationView()
        )

        print(
            "Persistent verification button registered."
        )


# ============================================================
# CREATE BOT
# ============================================================

bot = VerificationBot()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(
        f"Logged in as: {bot.user}"
    )
    print(
        f"Bot ID: {bot.user.id}"
    )
    print(
        "Verification bot is online!"
    )
    print("----------------------------------------")


# ============================================================
# SETUP VERIFICATION PANEL
# ============================================================

@bot.tree.command(
    name="setup-verification",
    description="Create the customer verification panel."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def setup_verification(
    interaction: discord.Interaction
):

    # ========================================================
    # CREATE WHITE EMBED
    # ========================================================

    embed = discord.Embed(
        title="Payment Verification",
        description=(
            "Have you purchased from us?\n\n"
            "Click **Claim Customer Role** below "
            "and enter your invoice ID to claim "
            "your **Customer** role."
        ),
        color=discord.Color.from_rgb(
            255,
            255,
            255
        )
    )

    embed.add_field(
        name="How it works",
        value=(
            "🛒 Click **Claim Customer Role**\n"
            "🧾 Enter your invoice ID\n"
            "✅ Receive the **Customer** role"
        ),
        inline=False
    )

    embed.set_footer(
        text="Customer Verification"
    )


    # ========================================================
    # SEND EMBED + BUTTON
    # ========================================================

    if interaction.channel is None:

        await interaction.response.send_message(
            "❌ I couldn't access this channel.",
            ephemeral=True
        )

        return


    await interaction.channel.send(
        embed=embed,
        view=VerificationView()
    )


    # ========================================================
    # CONFIRM TO ADMIN
    # ========================================================

    await interaction.response.send_message(
        "✅ Verification panel created.",
        ephemeral=True
    )


# ============================================================
# COMMAND ERROR
# ============================================================

@setup_verification.error
async def setup_verification_error(
    interaction: discord.Interaction,
    error
):

    print(
        f"Setup error: {error}"
    )

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        if not interaction.response.is_done():

            await interaction.response.send_message(
                "❌ You need Administrator permissions "
                "to use this command.",
                ephemeral=True
            )

        return


    if not interaction.response.is_done():

        await interaction.response.send_message(
            "❌ An error occurred while creating "
            "the verification panel.",
            ephemeral=True
        )


# ============================================================
# CHECK CONFIGURATION
# ============================================================

if not DISCORD_TOKEN:

    raise ValueError(
        "DISCORD_TOKEN is missing."
    )


if GUILD_ID == 0:

    raise ValueError(
        "GUILD_ID is missing or invalid."
    )


if CUSTOMER_ROLE_ID == 0:

    raise ValueError(
        "CUSTOMER_ROLE_ID is missing or invalid."
    )


# ============================================================
# START BOT
# ============================================================

print(
    "Starting verification bot..."
)

bot.run(
    DISCORD_TOKEN
)