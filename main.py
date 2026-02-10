import discord
from discord.ext import commands
import os
import json
import time
import asyncio

# ================= CONFIG =================
TOKEN = "MTQ1MDUyMTA4NTAzMTIxOTMxMg.Geu47t.p5jzyaHNRHJ0lboUYmdg3jHzoqdJglz5XE9viQ"
PREFIX = "$"
COOLDOWN = 60
VOUCH_TIME = 3600  # 1 hour gen-ban
CONFIG_FILE = "config.json"

CATEGORIES = ["free", "booster", "premium"]
ACCESS_FILE = "restock_access.json"
STOCK_DIR = "stock"

def load_access():
    if not os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "w") as f:
            json.dump({"users": []}, f)
    with open(ACCESS_FILE, "r") as f:
        return json.load(f)

def save_access(data):
    with open(ACCESS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def has_restock_access(member):
    data = load_access()
    return member.id in data["users"] or member.guild_permissions.administrator



# ================= CONFIG LOAD =================
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"guilds": {}}, f)

with open(CONFIG_FILE, "r") as f:
    CONFIG = json.load(f)

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(CONFIG, f, indent=4)

CATEGORY_EMOJIS = {
    "free": "<a:giftbox:1462345285618499675>",
    "booster": "<a:booster_evolution:1462342814204559443>",
    "premium": "<a:diamond_animated:1462343610556219436>"
}

CATEGORY_SERVICE_EMOJIS = {
    "free": "<:janky_sparkles:1462337786727104552>",
    "booster": "<:janky_sparkles_blue:1462340548869357610>",
    "premium": "<:janky_sparkles_purp:1462339343585640610>"
}


free = CATEGORY_EMOJIS["free"]
booster = CATEGORY_EMOJIS["booster"]
premium = CATEGORY_EMOJIS["premium"]

# ================= DATA =================
cooldowns = {}
pending_vouches = {}

# ================= BOT =================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# ================= SETUP =================
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):

    if ctx.author.id != 882509128013054013:
         return await ctx.send("❌ you cant use this command")

    gid = str(ctx.guild.id)

    CONFIG["guilds"][gid] = {
        "FREE_CHANNEL": None,
        "BOOSTER_CHANNEL": None,
        "VIP_CHANNEL": None,
        "VOUCH_CHANNEL": None,
        "LOG_CHANNEL": None,
        "RESTOCK_CHANNEL": None,
        "BOOSTER_ROLE": None,
        "PREMIUM_ROLE": None
    }

    questions = [
        ("Mention FREE GEN CHANNEL", "FREE_CHANNEL"),
        ("Mention BOOSTER GEN CHANNEL", "BOOSTER_CHANNEL"),
        ("Mention VIP GEN CHANNEL", "VIP_CHANNEL"),
        ("Mention VOUCH CHANNEL", "VOUCH_CHANNEL"),
        ("Mention LOG CHANNEL", "LOG_CHANNEL"),
        ("Mention RESTOCK ALERT CHANNEL", "RESTOCK_CHANNEL"),
        ("Mention BOOSTER ROLE", "BOOSTER_ROLE"),
        ("Mention VIP ROLE", "PREMIUM_ROLE")
    ]

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    for q, key in questions:
        await ctx.send(q)
        msg = await bot.wait_for("message", check=check, timeout=60)

        if "ROLE" in key:
            CONFIG["guilds"][gid][key] = msg.role_mentions[0].id
        else:
            CONFIG["guilds"][gid][key] = msg.channel_mentions[0].id

    save_config()
    await ctx.send("✅ Setup complete")

# ================= FILE PATH HELPER =================
def service_file(category, service):
    category = category.lower()
    service = service.lower()
    return f"{category}_{service}.txt"



#-==================R ACCESS=================

@bot.command()
@commands.has_permissions(administrator=True)
async def r_access(ctx, action: str, member: discord.Member):
    data = load_access()

    if action.lower() == "add":
        if member.id not in data["users"]:
            data["users"].append(member.id)
            save_access(data)
            await ctx.send(f"✅ {member.mention} now has restock access")
        else:
            await ctx.send("⚠️ user already has access")

    elif action.lower() == "remove":
        if member.id in data["users"]:
            data["users"].remove(member.id)
            save_access(data)
            await ctx.send(f"❌ restock access removed from {member.mention}")
        else:
            await ctx.send("⚠️ user doesn't have access")

    else:
        await ctx.send("❌ usage: `g!r_access <add/remove> <user>`")

# ================== DEL SERVICE ===========

@bot.command()
async def delservice(ctx, category: str, service: str):
    if not has_restock_access(ctx.author):
        return await ctx.send("❌ no restock access")

    category = category.lower()
    service = service.lower()

    if category not in CATEGORIES:
        return await ctx.send("❌ invalid category")

    path = service_file(category, service)


    if not os.path.exists(path):
        return await ctx.send("❌ service does not exist")

    os.remove(path)
    await ctx.send(f"🗑️ deleted service `{service}` from `{category}`")


# =-================addfile ==================

@bot.command()
async def addfile(ctx, category: str, service: str):
    if not has_restock_access(ctx.author):
        return await ctx.send("❌ no restock access")

    if not ctx.message.attachments:
        return await ctx.send("❌ attach a .txt file")

    file = ctx.message.attachments[0]
    if not file.filename.endswith(".txt"):
        return await ctx.send("❌ only .txt files allowed")

    category = category.lower()
    service = service.lower()

    # ✅ NEW FILE PATH (NO FOLDERS)
    path = service_file(category, service)

    content = (await file.read()).decode("utf-8")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)

    gid = str(ctx.guild.id)
    cfg = CONFIG["guilds"].get(gid)
    restock_channel = bot.get_channel(cfg["RESTOCK_CHANNEL"])

    embed = discord.Embed(
        title="🔔 Restock Alert",
        color=discord.Color.green()
    )
    embed.description = (
        f"**Restocked Service:** `{service}`\n"
        f"**Restocked by:** {ctx.author.mention}"
    )
    embed.set_footer(text="> @everyone")

    if restock_channel:
        await restock_channel.send(content="@everyone", embed=embed)


    # ================= ADD cat =================
@bot.command()
@commands.has_permissions(administrator=True)
async def addcategory(ctx, category, name):
    category = category.lower()
    name = name.lower()

    if category not in CATEGORIES:
        return await ctx.send("❌ invalid category")

    path = service_file(category, name)

    if os.path.exists(path):
        return await ctx.send("⚠️ service already exists")

    open(path, "w", encoding="utf-8").close()
    await ctx.send(f"✅ added `{name}` to `{category}`")





# ================= addstock =================

@bot.command()
async def addstock(ctx, category: str, service: str, *, text: str):
    if not has_restock_access(ctx.author):
        return await ctx.send("❌ no restock access")

    category = category.lower()
    service = service.lower()

    path = service_file(category, service)


    with open(path, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

    await ctx.send(f"✅ added stock to `{service}` ({category})")

    gid = str(ctx.guild.id)
    cfg = CONFIG["guilds"].get(gid)
    restock_channel = bot.get_channel(cfg["RESTOCK_CHANNEL"])

    embed = discord.Embed(
        title="🔔 Restock Alert",
        color=discord.Color.green()
    )
    embed.description = (
        f"**Restocked Service:** `{service}`\n"
        f"**Restocked by:** {ctx.author.mention}"
    )
    embed.set_footer(text="> @everyone")

    if restock_channel:
        await restock_channel.send(content="<@&1469260201256419404>", embed=embed)


# ================= GEN CORE =================

def has_required_status(member):
    REQUIRED = ".gg/YDwnfGuN3e BEST MCFA GEN SERVER"

    for act in member.activities:
        if isinstance(act, discord.CustomActivity):
            if act.name and REQUIRED.lower() in act.name.lower():
                return True
    return False

# ================= COPY BUTTON VIEW =================
class CopyView(discord.ui.View):
    def __init__(self, email, password, combo):
        super().__init__(timeout=None)
        self.email = email
        self.password = password
        self.combo = combo

    @discord.ui.button(label="Copy Email", style=discord.ButtonStyle.blurple)
    async def copy_email(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```{self.email}```", ephemeral=True)

    @discord.ui.button(label="Copy Password", style=discord.ButtonStyle.green)
    async def copy_password(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```{self.password}```", ephemeral=True)

    @discord.ui.button(label="Copy Combo", style=discord.ButtonStyle.gray)
    async def copy_combo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```{self.combo}```", ephemeral=True)


# ==================== HANDLE GEN ====================
async def handle_gen(ctx, category, service):
    gid = str(ctx.guild.id)
    cfg = CONFIG["guilds"].get(gid)
    if not cfg:
        return await ctx.send("❌ Bot not setup")

       # ===== CHANNEL CHECK =====
    if category.lower() == "free":
        if ctx.channel.id != cfg["FREE_CHANNEL"]:
            return

    elif category.lower() == "booster":
        if ctx.channel.id != cfg["BOOSTER_CHANNEL"]:
            return

    elif category.lower() == "premium":
        if ctx.channel.id != cfg["VIP_CHANNEL"]:
            return


    # ===== STATUS CHECK (FREE ONLY) =====
    if category.lower() == "free":
        if not has_required_status(ctx.author):
            return await ctx.send(
                "❌ Must have `.gg/YDwnfGuN3e BEST MCFA GEN SERVER` as status to generate"
            )


    # ===== ROLE CHECK =====
    roles = [r.id for r in ctx.author.roles]

    # FREE → everyone allowed
    if category.lower() == "free":
        pass

    # BOOSTER → booster OR vip
    elif category.lower() == "booster":
        if cfg["BOOSTER_ROLE"] not in roles and cfg["PREMIUM_ROLE"] not in roles:
            return await ctx.send("❌ Booster or VIP only")

    # VIP → vip only
    elif category.lower() == "premium":
        if cfg["PREMIUM_ROLE"] not in roles:
            return await ctx.send("❌ VIP only")


    # ===== GEN BAN & COOLDOWN (FOR ALL) =====
    banned = discord.utils.get(ctx.guild.roles, name="GEN-BANNED")
    if banned and banned in ctx.author.roles:
        return await ctx.send("❌ You are gen-banned")

    uid = ctx.author.id
    if uid in cooldowns and time.time() - cooldowns[uid] < COOLDOWN:
        return await ctx.send("⏳ Cooldown active")


    # STOCK FILE PATH
    file = service_file(category, service)

    if not os.path.exists(file):
        return await ctx.send("❌ Service not found")

    # READ FILE
    with open(file, encoding="utf-8") as f:
        raw = f.read()

    # CHECK IF CAPTURE FORMAT
    if "============================" in raw:
        # ======== CAPTURE BLOCK ========
        accounts = [a.strip() for a in raw.split("============================") if a.strip()]
        if not accounts:
            return await ctx.send("❌ Out of stock")

        account_raw = accounts.pop(0)

        # SAVE REMAINING
        with open(file, "w", encoding="utf-8") as f:
            f.write("\n\n============================\n\n".join(accounts))

        # BUILD EMBED
        def build_capture_embed(raw: str):
            lines = [l.strip() for l in raw.splitlines() if ":" in l]
            data = {}
            for l in lines:
                k, v = l.split(":", 1)
                data[k.strip()] = v.strip()

            email = data.pop("Email", "N/A")
            password = data.pop("Password", "N/A")
            combo = f"{email}:{password}"

            EMOJIS = {
                "Email": "📧", "Password": "🔑", "Name": "👤", "Capes": "🧢",
                "Account Type": "🧾", "Hypixel": "🎮", "Hypixel Level": "⭐",
                "First Hypixel Login": "📅", "Last Hypixel Login": "⏱️",
                "Optifine Cape": "🎨", "Email Access": "📬",
                "Hypixel Bedwars Stars": "🛏️", "Hypixel Banned": "🚫",
                "Can Change Name": "✏️", "Last Name Change": "🔁"
            }

            embed = discord.Embed(
                title="🎯 Vyra Capture Account",
                color=discord.Color.blurple()
            )
            embed.add_field(name="📧 Email", value=f"```{email}```", inline=True)
            embed.add_field(name="🔑 Password", value=f"```{password}```", inline=True)
            embed.add_field(name="🧩 Combo", value=f"```{combo}```", inline=False)

            items = list(data.items())
            for i in range(0, len(items), 3):
                chunk = items[i:i+3]
                value = "\n".join(f"{EMOJIS.get(k,'🔹')} **{k}**: `{v}`" for k, v in chunk)
                embed.add_field(name="—", value=value, inline=False)

            embed.set_footer(text="⚠️ Vouch within 1 hour or gen-ban applies")
            return embed

        dm_embed = build_capture_embed(account_raw)

    else:
        # ======== OLD SIMPLE LINE ========
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if not lines:
            return await ctx.send("❌ Out of stock")
        account_raw = lines.pop(0)

        # ===== SPLIT ACCOUNT =====
        if ":" in account_raw:
            email, password = account_raw.split(":", 1)
        else:
            email = account_raw
            password = "N/A"

        with open(file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        # basic embed
        dm_embed = discord.Embed(
            title="VyraG3N",
            color=discord.Color.blurple()
        )
        dm_embed.add_field(name="Service", value=f"```{service.upper()}```", inline=True)
        dm_embed.add_field(name="User", value=f"```{ctx.author.name}```", inline=True)
        dm_embed.add_field(name="Email", value=f"```{email}```", inline=False)
        dm_embed.add_field(name="Password", value=f"```{password}```", inline=False)
        dm_embed.add_field(name="Account", value=f"```{account_raw}```", inline=False)
        dm_embed.set_footer(text="⚠️ Vouch within 1 hour or gen-ban applies")

    # SEND DM
    try:
        view = CopyView(email, password, account_raw)
        await ctx.author.send(embed=dm_embed, view=view)

    except:
        return await ctx.send("❌ Cannot DM user")

    # CHANNEL EMBED
    channel_embed = discord.Embed(
        title="Account generated by VyraG3N, check DMs!",
        color=discord.Color.green()
    )
    channel_embed.add_field(name="Service", value=f"```{service.upper()}```", inline=True)
    channel_embed.add_field(name="Produced By", value=f"```{ctx.author.name}```", inline=True)
    channel_embed.set_footer(text="Vouch within 1h or ban!")
    await ctx.send(embed=channel_embed)

    # COOLDOWN & VOUCH TIMER
    pending_vouches[(uid, service)] = time.time()
    cooldowns[uid] = time.time()
    asyncio.create_task(vouch_timer(ctx.guild, ctx.author, service))




# ================= GEN COMMANDS =================
@bot.command()
async def free(ctx, service: str):
    await handle_gen(ctx, "Free", service)

@bot.command()
async def booster(ctx, service: str):
    await handle_gen(ctx, "Booster", service)

@bot.command()
async def premium(ctx, service: str):
    await handle_gen(ctx, "Premium", service)

# ================= VOUCH TIMER =================
async def vouch_timer(guild, member, service):
    await asyncio.sleep(VOUCH_TIME)

    key = (member.id, service)
    if key not in pending_vouches:
        return

    pending_vouches.pop(key)

    role = discord.utils.get(guild.roles, name="GEN-BANNED")
    if not role:
        role = await guild.create_role(name="GEN-BANNED")

    await member.add_roles(role)

    await asyncio.sleep(3600)
    await member.remove_roles(role)

# ================= VOUCH CHECK =================
@bot.event
async def on_message(msg):
    await bot.process_commands(msg)

    if msg.author.bot:
        return

    for (uid, service) in list(pending_vouches.keys()):
        if msg.content.strip() == f"Legit got {service.upper()} from <@{1450521085031219312}>":
            pending_vouches.pop((uid, service))
            await msg.channel.send("✅ Vouch accepted")




# ================= STOCK =================
@bot.command()
async def stock(ctx):
    embed = discord.Embed(
        title="<:vyra:1460637993181253845> VyraG3N <:vyra:1460637993181253845>",
        description=" ```Current Generator Stock```\n\u200b",
        color=discord.Color.green()
    )

    for cat in CATEGORIES:
        services = []

        for file in os.listdir():
            if file.startswith(f"{cat}_") and file.endswith(".txt"):
                service_name = file.replace(f"{cat}_", "").replace(".txt", "")

                with open(file, encoding="utf-8") as f:
                    count = len([l for l in f if l.strip()])

                services.append(
                    f"{CATEGORY_SERVICE_EMOJIS[cat]} {service_name} → `{count}`"
                )

        if not services:
            services.append("— Empty —")

        embed.add_field(
            name=f"{CATEGORY_EMOJIS[cat]} **{cat.upper()}**",
            value="\n".join(services) + "\n\u200b",
            inline=False
        )

    embed.set_footer(text="💡 Vouch within 1 hour or gen-ban applies!")
    await ctx.send(embed=embed)




# ================= HELP =================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Commands")
    for c in bot.commands:
        embed.add_field(name=PREFIX + c.name, value=c.help or "—", inline=False)
    await ctx.send(embed=embed)

# ================= RUN =================
bot.run(TOKEN)
