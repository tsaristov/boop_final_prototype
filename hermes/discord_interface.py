import discord
from discord.ext import commands
import requests
import json
import asyncio

# Bot configuration
TOKEN = ""
API_URL = "http://0.0.0.0:8003/detect-intent"  # Updated FastAPI endpoint

# Define bot intents
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.messages = True
intents.guilds = True
intents.message_content = True  # Required for message content access

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """Triggered when the bot is ready."""
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')

async def send_bot_message(channel, content):
    """
    Sends a message from the bot to the specified channel.
    """
    await channel.send(content)  # Send the message content to the channel

@bot.event
async def on_message(message):
    """Triggered when a message is received."""
    if message.author.bot:  # Ignore messages from bots
        return

    user_input = message.content  # Get the content of the received message
    user_name = message.author.name  # Get the author's name
    user_id = str(message.author.id)  # Get the author's ID
    channel = message.channel  # Get the channel

    try:
        # Send the message to the FastAPI server
        response = requests.post(API_URL, json={
            "message": user_input,
            "user_name": user_name,
            "user_id": user_id
        })
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()  # Parse the JSON response

        # Access the assistant's reply
        assistant_reply = data.get("message", "No response")  # Get the assistant's reply
        await send_bot_message(channel, assistant_reply)  # Send the assistant's reply to the channel

    except requests.exceptions.RequestException as e:
        await send_bot_message(channel, f"Error connecting to the API: {e}")
    except json.JSONDecodeError:
        await send_bot_message(channel, "Invalid response format from the API.")

# Run the bot
bot.run(TOKEN)
