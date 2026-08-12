import os

import discord
from discord import app_commands
import stripe
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
GUILD_ID = int(os.getenv("GUILD_ID"))
CUSTOMER_ROLE_ID = int(os.getenv("CUSTOMER_ROLE_ID"))

stripe.api_key = STRIPE_SECRET_KEY


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
# VERIFICATION VIEW
# ============================================================

class VerificationView(discord.ui.View):

    def __init__(self):
        # IMPORTANT:
        # timeout=None makes this a persistent view.
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

        self.add_item(
            self.invoice_id
        )


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
        # CHECK IF INVOICE IS PAID
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
        # GET INVOICE METADATA
        # ====================================================

        metadata = invoice.get(
            "metadata",
            {}
        )

        discord_user_id = metadata.get(
            "discord_user_id"
        )


        # ====================================================
        # CHECK IF INVOICE IS LINKED
        # ====================================================

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
        # CHECK DISCORD USER ID
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
        # GET SERVER
        # ====================================================

        guild = interaction.guild

        if guild is None:

            await interaction.followup.send(
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

            embed = discord.Embed(
                title="❌ Error",
                description=(
                    "I couldn't find you in this server."
                ),
                color=discord.Color.red()
            )

            await interaction.followup.send(
                embed=embed,
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

            await interaction.followup.send(
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

        except discord.HTTPException:

            embed = discord.Embed(
                title="❌ Discord Error",
                description=(
                    "Discord couldn't give you the role.\n\n"
                    "Please try again."
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

        embed.add_field(
            name="Invoice",
            value=f"`{invoice_id}`",
            inline=False
        )

        embed.set_footer(
            text="Stripe Payment Verification"
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )


# ============================================================
# DISCORD BOT
# ============================================================

class StripeBot(discord.Client):

    def __init__(self):

        intents = discord.Intents.default()

        super().__init__(
            intents=intents
        )

        self.tree = app_commands.CommandTree(
            self
        )


    # ========================================================
    # BOT STARTUP
    # ========================================================

    async def setup_hook(self):

        guild = discord.Object(
            id=GUILD_ID
        )

        # Sync slash commands
        self.tree.copy_global_to(
            guild=guild
        )

        await self.tree.sync(
            guild=guild
        )

        # ====================================================
        # IMPORTANT RAILWAY FIX
        # ====================================================
        #
        # Register the persistent button when the bot starts.
        #
        # Without this, Discord can display the button but
        # the bot won't know what to do when someone clicks it
        # after a restart/redeploy.
        #
        self.add_view(
            VerificationView()
        )

        print("Persistent verification button registered.")


# ============================================================
# CREATE BOT
# ============================================================

bot = StripeBot()


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print("----------------------------------------")
    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Bot is online!")
    print("----------------------------------------")


# ============================================================
# SETUP VERIFICATION PANEL
# ============================================================

@bot.tree.command(
    name="setup-verification",
    description="Create the Stripe customer verification panel."
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
            "Click **Claim Customer Role** below "
            "and enter your Stripe invoice ID.\n\n"
            "Your payment will be checked securely "
            "through Stripe."
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
            "1. Click **Claim Customer Role**\n"
            "2. Enter your Stripe invoice ID\n"
            "3. We'll verify your payment\n"
            "4. Receive the **Customer** role"
        ),
        inline=False
    )

    embed.set_footer(
        text="Stripe Payment Verification"
    )

    # Send the panel
    await interaction.channel.send(
        embed=embed,
        view=VerificationView()
    )

    await interaction.response.send_message(
        "✅ Verification panel created.",
        ephemeral=True
    )


# ============================================================
# SETUP COMMAND ERROR
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

    else:

        print(
            f"Setup command error: {error}"
        )


# ============================================================
# CHECK CONFIG
# ============================================================

if not DISCORD_TOKEN:

    raise ValueError(
        "DISCORD_TOKEN is missing from Railway variables."
    )


if not STRIPE_SECRET_KEY:

    raise ValueError(
        "STRIPE_SECRET_KEY is missing from Railway variables."
    )


# ============================================================
# START BOT
# ============================================================

print("Starting Stripe Discord Bot...")

bot.run(
    DISCORD_TOKEN
)