import os

import discord
from discord import app_commands
import stripe
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

GUILD_ID = int(os.getenv("GUILD_ID"))
CUSTOMER_ROLE_ID = int(os.getenv("CUSTOMER_ROLE_ID"))

stripe.api_key = STRIPE_SECRET_KEY


# ============================================================
# BOT
# ============================================================

class StripeBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()

        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)

        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


bot = StripeBot()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("--------------------------------")
    print(f"Logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("--------------------------------")


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

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.send_modal(
            InvoiceModal()
        )


# ============================================================
# BUTTON VIEW
# ============================================================

class VerificationView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

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
            label="Stripe Invoice ID",
            placeholder="Example: in_123456789",
            required=True,
            min_length=5,
            max_length=255
        )

        self.add_item(self.invoice_id)


    async def on_submit(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer(
            ephemeral=True
        )

        invoice_id = self.invoice_id.value.strip()


        # ====================================================
        # GET STRIPE INVOICE
        # ====================================================

        try:

            invoice = stripe.Invoice.retrieve(
                invoice_id
            )

        except stripe.error.InvalidRequestError:

            embed = discord.Embed(
                title="❌ Verification Failed",
                description=(
                    "I couldn't find that Stripe invoice.\n\n"
                    "Please make sure you entered the "
                    "correct invoice ID."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        except stripe.error.StripeError:

            embed = discord.Embed(
                title="❌ Stripe Error",
                description=(
                    "Stripe couldn't be contacted right now.\n\n"
                    "Please try again later."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # CHECK PAYMENT
        # ====================================================

        if invoice.status != "paid":

            embed = discord.Embed(
                title="❌ Payment Not Verified",
                description=(
                    "This invoice has not been successfully paid."
                ),
                color=discord.Color.red()
            )

            embed.add_field(
                name="Invoice Status",
                value=f"`{invoice.status}`",
                inline=False
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # CHECK DISCORD ID
        # ====================================================

        metadata = invoice.get(
            "metadata",
            {}
        )

        discord_user_id = metadata.get(
            "discord_user_id"
        )


        if not discord_user_id:

            embed = discord.Embed(
                title="❌ Invoice Not Linked",
                description=(
                    "This invoice is paid, but it isn't "
                    "linked to a Discord account.\n\n"
                    "Please contact support."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # MAKE SURE INVOICE BELONGS TO USER
        # ====================================================

        if str(discord_user_id) != str(
            interaction.user.id
        ):

            embed = discord.Embed(
                title="❌ Verification Denied",
                description=(
                    "This invoice belongs to a different "
                    "Discord account."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # GET GUILD
        # ====================================================

        guild = interaction.guild

        if guild is None:

            await interaction.followup.send(
                "❌ This can only be used inside the server.",
                ephemeral=True
            )

            return


        # ====================================================
        # GET ROLE
        # ====================================================

        role = guild.get_role(
            CUSTOMER_ROLE_ID
        )

        if role is None:

            embed = discord.Embed(
                title="❌ Configuration Error",
                description=(
                    "The Customer role could not be found."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # GET MEMBER
        # ====================================================

        member = guild.get_member(
            interaction.user.id
        )

        if member is None:

            await interaction.followup.send(
                "❌ I couldn't find you in this server.",
                ephemeral=True
            )

            return


        # ====================================================
        # ALREADY HAS ROLE
        # ====================================================

        if role in member.roles:

            embed = discord.Embed(
                title="✅ Already Verified",
                description=(
                    "You already have the **Customer** role."
                ),
                color=discord.Color.green()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # GIVE ROLE
        # ====================================================

        try:

            await member.add_roles(
                role,
                reason=(
                    f"Verified Stripe invoice "
                    f"{invoice_id}"
                )
            )

        except discord.Forbidden:

            embed = discord.Embed(
                title="❌ Permission Error",
                description=(
                    "I don't have permission to give "
                    "you the Customer role.\n\n"
                    "Make sure the bot's role is above "
                    "the Customer role."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

            return


        # ====================================================
        # SUCCESS
        # ====================================================

        embed = discord.Embed(
            title="✅ Customer Role Claimed",
            description=(
                "Your Stripe payment has been successfully "
                "verified!\n\n"
                "You have been given the **Customer** role."
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Stripe Payment Verification"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# SETUP COMMAND
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

    embed = discord.Embed(
        title="Payment Verification",
        description=(
            "Have you purchased from us?\n\n"
            "Click the button below and enter your "
            "Stripe invoice ID to claim your "
            "**Customer** role.\n\n"
            "Your payment will be checked securely "
            "through Stripe."
        ),
        color=discord.Color.from_rgb(
            255,
            255,
            255
        )
    )

    embed.set_footer(
        text="Stripe Payment Verification"
    )

    await interaction.channel.send(
        embed=embed,
        view=VerificationView()
    )

    await interaction.response.send_message(
        "✅ Verification panel created.",
        ephemeral=True
    )


# ============================================================
# ERROR HANDLER
# ============================================================

@setup_verification.error
async def setup_verification_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        await interaction.response.send_message(
            "❌ You need Administrator permissions "
            "to use this command.",
            ephemeral=True
        )


# ============================================================
# RUN
# ============================================================

if not DISCORD_TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is missing from .env"
    )

if not STRIPE_SECRET_KEY:
    raise ValueError(
        "STRIPE_SECRET_KEY is missing from .env"
    )


bot.run(DISCORD_TOKEN)