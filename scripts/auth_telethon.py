import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = 37884291
API_HASH = '988f336fb2034fefe700fc6cdf4f3513'
SESSION_FILE = 'telegram_session_string.txt'


async def main():
    print('=' * 50)
    print('Telethon Auth — QR Login')
    print('=' * 50)
    print('Akan muncul QR code di terminal, scan pake Telegram mobile.')
    print()

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    print(f'\n✅ Login berhasil: {me.first_name} (@{me.username})')

    session_str = client.session.save()
    with open(SESSION_FILE, 'w') as f:
        f.write(session_str)
    print(f'✅ Session saved ke {SESSION_FILE}')

    await client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
